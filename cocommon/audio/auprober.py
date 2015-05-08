#! /usr/bin/env python3

import logging
import json
import os
import traceback
import argparse
import time
import pprint
import xml.etree.ElementTree as ET

from ..utils import tricks
from ..utils.compat import subprocess

WEIGHT_OF_CODEC = {
    'aac': 1.2,
    'vorbis': 1.2,
    'default': 1,
}


class AudioProber(object):

    """Audio Prober for local files and urls (only for ffprobe/avprobe)

    We only care about tracks rather than container
    """

    def __init__(self, fn, input_options=[], prober='ffprobe', timeout=5):
        super(AudioProber, self).__init__()
        self.fn = fn
        self._input_options = input_options
        self._prober = prober
        self._timeout = timeout
        self._track_list = None
        self._best_track = None
        self._logger = logging.getLogger(__name__)

    def get_audio_track_list(self, prober='ffprobe', retry_times=5, timeout=5):
        """Probe an audio file to get all audio tracks"""
        # ffmpeg and libav share same interface
        if not timeout:
            timeout = self._timeout
        track_list = None
        if prober is None:
            prober = self._prober
        if prober in ('ffprobe', 'avprobe'):
            if self._track_list:
                return self._track_list
            cmd = [prober] + self._input_options + [self.fn] + [
                '-show_entries', 'format:stream', '-print_format', 'json']
            json_data = None
            try:
                json_data = tricks.retry(
                    retry_times, subprocess.check_output, cmd, timeout=timeout)
                if json_data:
                    data = json.loads(json_data.decode('utf-8', 'ignore'))
                else:
                    raise Exception("Invalid source {}".format(self.fn))

                track_list = []
                for i in data['streams']:
                    if i.get('codec_type') == 'audio':
                        track = {}
                        track['codec'] = i.get('codec_name', '')
                        track['bit_rate'] = int(float(
                            i.get('bit_rate',
                                  data['format'].get('duration', 0))))
                        track['sample_rate'] = int(i.get('sample_rate', 0))
                        track['channels'] = int(i.get('channels', 0))
                        track['duration'] = float(
                            i.get('duration',
                                  data['format'].get('duration', 0)))
                        track['index'] = int(i.get('index', 0))
                        track['format_name'] = data[
                            'format'].get('format_name', '')
                        track_list.append(track)
                self._track_list = track_list
            except subprocess.CalledProcessError as e:
                self._logger.warning('Called Process Error: %s', e)
            except subprocess.TimeoutExpired as e:
                self._logger.warning('Timeout Expired: %s', e.cmd)
            except Exception as e:
                self._logger.error(
                    '%s\n' + '-' * 50 + '\n%s', cmd, traceback.format_exc())
        elif prober == 'mediainfo':
            if not self.fn or not os.path.isfile(self.fn):
                self._logger.warning('No such file %s', self.fn)
                return []
            try:
                cmd = [prober, "--Output=XML", self.fn]
                xml_output = tricks.retry(
                    retry_times, subprocess.check_output, cmd, timeout=timeout)
                etree = ET.fromstring(xml_output)
                track_list = []
                for i in etree.iter('track'):
                    if i.attrib['type'] != 'Audio':
                        continue
                    track = {}
                    for node in i:
                        track[node.tag] = node.text
                    track_list.append(track)
            except subprocess.CalledProcessError as e:
                self._logger.warning(e)
            except subprocess.TimeoutExpired as e:
                self._logger.warning('Timeout Expired: %s', e.cmd)
            except Exception as e:
                self._logger.warning(traceback.format_exc())
        return track_list

    def get_best_track(self, retry_times=5, timeout=5, flush=False):
        if not flush and self._best_track:
            return self._best_track
        if flush or not self._track_list:
            self.get_audio_track_list(retry_times=retry_times, timeout=timeout)
        if not self._track_list:
            return {}
        tmp_tracks = []
        # Calculate longest duration
        max_duration = 0
        for track in self._track_list:
            if track['duration'] > max_duration:
                max_duration = track['duration']
        # Calculate value of valid tracks
        for track in self._track_list:
            if max_duration - track['duration'] < 1:
                track['value'] = float(
                        track['bit_rate']) * WEIGHT_OF_CODEC.get(
                            track['codec'], WEIGHT_OF_CODEC['default'])
                tmp_tracks.append(track)

        best_track = max(tmp_tracks, key=lambda x: x['value'])
        del best_track['value']
        self._best_track = best_track
        return best_track

    def get_aac_profile(self, track_index=0):
        """Get profile of aac if specified track is aac"""
        if not os.path.isfile(self.fn):
            self._logger.warning(
                'Can only get profile of local file')
            return
        if self._track_list is None:
            self.get_audio_track_list(prober='ffprobe')
        if not self._track_list or len(self._track_list) < track_index + 1:
            self._logger.warning(
                'No suck track [%s] among %s', track_index, self._track_list)
            return
        track = self._track_list[track_index]
        if track['codec'] != 'aac':
            self._logger.info('Not aac track [%s]', track)
            return 'non-aac'
        mediainfo_track = self.get_audio_track_list(
            prober='mediainfo')[track_index]
        self._logger.info(pprint.pformat(mediainfo_track))
        # mediainfo_track commonly have correct probe output
        if 'HE-AACv2' in mediainfo_track['Format_profile']:
            return 'aac_he_v2'
        elif 'HE-AAC' in mediainfo_track['Format_profile']:
            return 'aac_he'
        elif 'LC' in mediainfo_track['Format_profile']:
            return 'lc'
        self._logger.warning(
            'Mediainfo output is not correct, getting clues from comparison')
        # Compare output of ffprobe/avprobe and mediainfo to get aac profile
        # HE-AACv2: check number of channels
        nchannels = int(track['channels'])
        if 'Channel_s_' in mediainfo_track:
            nchannels_tag_name = 'Channel_s_'
        elif 'Channel_count' in mediainfo_track:
            nchannels_tag_name = 'Channel_count'
        else:
            raise Exception("Unsupported version of mediainfo")
        mediainfo_nchannels = int(
            mediainfo_track[nchannels_tag_name][
                :mediainfo_track[nchannels_tag_name].find(' ')])
        if nchannels != mediainfo_nchannels:
            return 'aac_he_v2'
        # HE-AAC: check sample_rate
        sample_rate = int(track['sample_rate'])
        mediainfo_sample_rate = mediainfo_track[
            'Sampling_rate'].split(' / ')[0]
        if mediainfo_sample_rate.endswith('KHz'):
            mediainfo_sample_rate = float(
                mediainfo_sample_rate.split()[0]) * 1000
        else:
            mediainfo_sample_rate = float(mediainfo_sample_rate.split()[0])
        if sample_rate > 1.2 * mediainfo_sample_rate:
            return 'aac_he'
        return 'lc'


def select_best_protocol_for_stream(url, i_options=[],
                                    retry_times=5, timeout=10):
    """Probe a list of possible urls for <url>.

    rtsp or mmsh for mms
    http or mmsh for http

    :param url: stream url
    :param i_options: input options
    :param retry_times: times to repeat the test
    :param timeout: probe timeout"""
    logger = logging.getLogger(__name__)
    time_punishment = 100
    result = []
    if '://' not in url:  # local file
        audio_prober = AudioProber(url, i_options)
        track_info = audio_prober.get_best_track()
        (track_info['selected_protocol'], track_info['con_time']) = ('file', 0)
        return track_info

    if not tricks.is_ascii(url):
        url = tricks.url_fix(url)

    (proto, rest) = url.split('://', 1)
    # rtspu is rare, so treat all rtsp streams as rtspt
    proto = proto.replace('rtspt', 'rtsp').replace('rtmpt', 'rtmp')

    # list possible protos
    if proto == 'rtmp':
        possible_protos = ['rtmp']
    elif proto == 'http':
        possible_protos = ['http', 'mmsh']
    elif proto in ['mms', 'mmsh', 'mmst', 'rtsp']:
        possible_protos = ['rtsp', 'mmsh']
    else:
        logger.warning("Protocol %s not supported", proto)

    track_info = None
    for p in possible_protos:
        input_options = list(i_options)  # copy i_options
        if p == 'rtmp' and 'live=1' not in rest:
            rest += ' live=1'
        if p == 'rtsp' and '-rtsp_transport' not in input_options:
            input_options = ['-rtsp_transport', 'tcp']

        tmp = []
        valid = False
        for i in range(retry_times):
            start_time = time.time()
            audio_prober = AudioProber(
                '{}://{}'.format(p, rest), input_options)
            best_track = audio_prober.get_best_track(
                retry_times=1, timeout=timeout, flush=True)
            if best_track:
                tmp.append(time.time() - start_time)
                track_info = dict(best_track)
                valid = True
            else:
                tmp.append(time_punishment)  # probe failed
        logger.info('%s://%s, %s', p, rest, tmp)
        if valid:
            result.append((p, sum(tmp) / len(tmp)))

    if result:
        (track_info['selected_protocol'], track_info['con_time']) = min(
            result, key=lambda x: x[1])
        return track_info

    raise Exception('No available track for {}'.format(url))


def main():
    # set up argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('file', help='local file to probe')
    args = parser.parse_args()

    # set up logging
    log_format = '[%(levelname)s]-%(funcName)s: %(message)s --- %(asctime)s'
    log_formatter = logging.Formatter(log_format)
    logstream_handler = logging.StreamHandler()
    logstream_handler.setFormatter(log_formatter)
    logstream_handler.setLevel(logging.DEBUG)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logstream_handler)
    logger.info('-' * 40 + '<%s>' + '-' * 40, time.asctime())
    logger.info('Arguments: %s', args)

    p = AudioProber(args.file)
    p.get_audio_track_list()
    for track in p._track_list:
        logger.info('-' * 3 + ' %s ' + '-' * 3 + ' %s', track,
                    str(p.get_aac_profile(track['index'])))


if __name__ == '__main__':
    main()
