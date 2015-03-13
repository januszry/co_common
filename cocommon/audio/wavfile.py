#! /usr/bin/env python3

import wave
import argparse
import logging
import logging.handlers
import os
import time
import subprocess
import traceback

from ..utils import tricks


NFRAMES_DEFAULT = 500 << 10
LOUD_BOUND_DEFAULT = 512
INVERT_BOUND_DEFAULT = 1024
SKIP_FRAMES_DEFAULT = 100000


class WavFile(object):
    """A wave file checker

    Checks channels, if inverted, if onesided, volume and loudness
    :param fn: file name
    :param n_tested_frames: number of tested frames
    """

    def __init__(self, fn, n_tested_frames=NFRAMES_DEFAULT):
        super(WavFile, self).__init__()
        self._fn = fn
        self.n_tested_frames = n_tested_frames
        self.n_channels = None
        self.loudness = None
        self.loudness_range = None
        self.loudness_range_low = None
        self.loudness_range_high = None
        self.volume_mean = None
        self.volume_max = None
        self.n_valid_frames = None
        self.n_inverted_frames = None
        self.n_ll_frames = None
        self.n_rr_frames = None
        self._logger = logging.getLogger(__name__)

    def __str__(self):
        slist = ['\n{}'.format(str(self._fn)),
                 '=' * 50,
                 'n_channels: {}'.format(self.n_channels),
                 'n_tested_frames: {}'.format(self.n_tested_frames),
                 'n_valid_frames: {}'.format(self.n_valid_frames),
                 'n_inverted_frames: {}'.format(self.n_inverted_frames),
                 'n_ll_frames: {}'.format(self.n_ll_frames),
                 'n_rr_frames: {}'.format(self.n_rr_frames),
                 '-' * 50,
                 'AlwaysLow: {}'.format(self.is_always_low),
                 'Inverted: {}'.format(self.is_inverted),
                 'LL: {}'.format(self.is_ll),
                 'RR: {}'.format(self.is_rr),
                 '-' * 50,
                 'Volume Mean: {}'.format(self.volume_mean),
                 'Volume Max: {}'.format(self.volume_max),
                 'Loudness Integrated (LUFS): {}'.format(self.loudness),
                 'Loudness Range: {}'.format(self.loudness_range),
                 'Loudness Range Low: {}'.format(self.loudness_range_low),
                 'Loudness Range High: {}'.format(self.loudness_range_high),
                 ]
        return '\n'.join(slist)

    @property
    def wav_info(self):
        """A dictionary description of wave file"""
        return {'wav_loudness': self.loudness,
                'wav_loudness_range': self.loudness_range,
                'wav_loudness_range_high': self.loudness_range_high,
                'wav_loudness_range_low': self.loudness_range_low,
                'wav_volume_max': self.volume_max,
                'wav_volume_mean': self.volume_mean,
                'wav_inverted_frames': self.n_inverted_frames,
                'wav_ll_frames': self.n_ll_frames,
                'wav_rr_frames': self.n_rr_frames,
                'wav_is_inverted': self.is_inverted,
                'wav_is_ll': self.is_ll,
                'wav_is_rr': self.is_rr,
                'wav_tested_frames': self.n_tested_frames,
                'wav_valid_frames': self.n_valid_frames,
                }

    @property
    def is_inverted(self):
        """Inverted check."""
        if self.n_channels != 2:
            return False
        if not self.n_valid_frames or \
                self.n_valid_frames << 3 <= self.n_tested_frames or \
                not self.n_inverted_frames:
            return False
        if self.is_ll or self.is_rr:
            return False
        # TODO: ratio
        return self.n_inverted_frames * 1.6 >= self.n_valid_frames

    @property
    def is_ll(self):
        """Onesided (L) check."""
        if self.n_channels != 2:
            return False
        if not self.n_valid_frames or \
                self.n_valid_frames << 3 <= self.n_tested_frames or \
                not self.n_ll_frames:
            return False
        return self.n_ll_frames >= self.n_valid_frames >> 2 and \
            self.n_ll_frames >= self.n_rr_frames << 2

    @property
    def is_rr(self):
        """Onesided (R) check."""
        if self.n_channels != 2:
            return False
        if not self.n_valid_frames or \
                self.n_valid_frames << 3 <= self.n_tested_frames or \
                not self.n_rr_frames:
            return False
        return self.n_rr_frames >= self.n_valid_frames >> 2 and \
            self.n_rr_frames >= self.n_ll_frames << 2

    @property
    def is_always_low(self):
        """Too low volume check."""
        if self.n_valid_frames is None or self.n_channels != 2:
            return False
        return self.n_valid_frames <= self.n_tested_frames >> 10

    def check_wave_file(self, check_volume=False, check_loudness=False,
                        loud_bound=LOUD_BOUND_DEFAULT, timeout=30):
        """Main entrance.

        :param check_volume: flag, if set,
            check volume with ffmpeg and volume filter
        :param check_loudness: flag, if set,
            check loudness with ffmpeg and ebur128
        :param loud_bound: if volume of a channel if over this bound,
            this frame is too loud
        :param timeout: a timeout to prevent from zombie ffmpeg"""
        if not os.path.isfile(self._fn):
            self._logger.warning("No such file: %s", self._fn)
            return
        wave_f = wave.open(self._fn, 'rb')
        wave_info = get_info(wave_f)
        self.n_channels = wave_info['n_channels']

        if check_volume:
            (self.volume_mean, self.volume_max) = get_volume(self._fn, timeout)
        if check_loudness:
            (self.loudness, self.loudness_range, self.loudness_range_low,
             self.loudness_range_high) = get_volume_lufs(self._fn, timeout)

        if self.n_channels != 2:
            self._logger.warning(
                'Only files with 2 channels need further check')
            return
        if wave_info['n_frames'] < SKIP_FRAMES_DEFAULT:
            self._logger.warning('File Too Short')
            return

        self._logger.info('Checking channels for %s', self._fn)

        if not self.n_tested_frames or \
                self.n_tested_frames > wave_info[
                        'n_frames'] - SKIP_FRAMES_DEFAULT:
            self.n_tested_frames = wave_info['n_frames'] - SKIP_FRAMES_DEFAULT

        wave_f.readframes(SKIP_FRAMES_DEFAULT)

        width = wave_info['n_sample_bits']

        up = 1 << width * 8
        _max = 1 << (width * 8 - 1)

        n_valid_frames = 0
        n_inverted_frames = 0
        n_ll_frames = 0
        n_rr_frames = 0

        for i in range(self.n_tested_frames):
            frame = wave_f.readframes(1)
            if isinstance(frame, str):
                get_int = lambda x: get_int(x)
            elif isinstance(frame, bytes):
                get_int = lambda x: x

            if len(frame) == 0:
                continue

            left = frame[:width]
            right = frame[width:]

            left_data = get_int(left[-1])
            for j in range(width - 1):
                left_data = left_data * 256 + get_int(left[-j - 2])
            if left_data <= _max:
                left_data_abs = left_data
            else:
                left_data_abs = up - left_data

            right_data = get_int(right[-1])
            for j in range(width - 1):
                right_data = right_data * 256 + get_int(right[-j - 2])
            if right_data < _max:
                right_data_abs = right_data
            else:
                right_data_abs = up - right_data

            # small sounds and too loud sounds ignored
            if left_data_abs > loud_bound or right_data_abs > loud_bound:
                if left_data_abs == _max or right_data_abs == _max:
                    continue
                n_valid_frames += 1

                if _judge_frame_inverted(left_data, right_data, _max):
                    n_inverted_frames += 1

                onesided = _judge_frame_onesided(left_data_abs, right_data_abs)
                if onesided == 'LL':
                    n_ll_frames += 1
                elif onesided == 'RR':
                    n_rr_frames += 1

        self.n_valid_frames = n_valid_frames
        self.n_inverted_frames = n_inverted_frames
        self.n_ll_frames = n_ll_frames
        self.n_rr_frames = n_rr_frames


def get_info(f):
    info = {}
    info['n_channels'] = f.getnchannels()
    info['n_sample_bits'] = f.getsampwidth()
    info['n_frames'] = f.getnframes()
    info['frame_rate'] = f.getframerate()
    info['compression_type'] = f.getcomptype()
    info['compression_name'] = f.getcompname()
    return info


def _judge_frame_inverted(left_data, right_data, _max):
    """Judge if frame is inverted.

    left_data and right_data are all unsigned decimal numbers
    if data is larger than _max, its wave is in negative direction"""
    # if left and right data are in the same direction
    if (left_data >= _max and right_data >= _max) or \
            (left_data < _max and right_data < _max):
        return False
    if _max * 2 - (left_data + right_data) <= INVERT_BOUND_DEFAULT:
        return True
    return False


def _judge_frame_onesided(left_data_abs, right_data_abs):
    """Judge if one channel is much louder than the other.

    left_data_abs and right_data_abs are both abs(
    signed number of left_data and right_data)"""
    if left_data_abs >> 2 > right_data_abs:
        return 'LL'
    elif right_data_abs >> 2 > left_data_abs:
        return 'RR'
    return None


def get_volume(fn, timeout=30):
    """Get volume with ffmpeg filter volumedetect"""
    logger = logging.getLogger(__name__)
    cmd = ['ffmpeg', '-i', fn, '-af',
           'volumedetect', '-f', 'null', '/dev/null']
    logger.info(
        'Checking volume of %s with ffmpeg and volumedetect filter', fn)
    try:
        output = subprocess.check_output(
            cmd, timeout=timeout, stderr=subprocess.STDOUT).splitlines()
        for line in output:
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            line = line.rstrip()
            if 'mean_volume: ' in line:
                vmean = float(line.split()[-2])
            elif 'max_volume: ' in line:
                vmax = float(line.split()[-2])
        return [vmean, vmax]
    except:
        logger.warning(traceback.format_exc())
        return [None] * 2


def get_volume_lufs(fn, timeout=30):
    """Get volume with EBU-r128"""
    logger = logging.getLogger(__name__)
    cmd = [
        'ffprobe', '-v', 'error', '-of', 'compact=p=0:nk=1', '-show_entries',
        'frame_tags=lavfi.r128.I,lavfi.r128.LRA,lavfi.r128.LRA.low,lavfi.r128.LRA.high',
        '-f', 'lavfi', 'amovie={},ebur128=metadata=1'.format(fn)]
    logger.info('Checking loudness of %s with ffmpeg and ebur128 filter', fn)
    try:
        output = subprocess.check_output(cmd, timeout=timeout)
    except:
        logger.warning(traceback.format_exc())
        return [None] * 4

    for line in output.splitlines():
        sline = line.rstrip()
        if sline:
            tmp = sline
    logger.info("Last line of get_volume: %s", tmp)
    try:
        return [float(i) for i in tmp.split('|')]
    except TypeError:
        return [float(i) for i in tmp.decode('utf-8').split('|')]


def generate_wav_file(src, fn, input_options=[], output_options=[],
                      retry_times=5, timeout=30):
    """Generate wav file with FFMPEG.

    from <src>, with <input_options> into <fn>"""
    tmp_fn = '{}_{}'.format(fn, int(time.time()))
    tmp_input_options = list(input_options)
    tmp_output_options = list(output_options)
    if '-aframes' not in tmp_output_options \
            and '-frames:a' not in tmp_output_options \
            and '-fs' not in tmp_output_options:
        if '-t' not in tmp_output_options:
            tmp_output_options += ['-t', '7']
        if 'asetpts=FRAME_RATE' not in tmp_output_options:
            tmp_output_options += ['-af', 'asetpts=FRAME_RATE']
    src = src.replace('rtspt://', 'rtsp://').replace('rtmpt://', 'rtmp://')
    if src.startswith('rtsp://') and \
            '-rtsp_transport' not in tmp_input_options:
        tmp_input_options += ['-rtsp_transport', 'tcp']
    elif src.startswith('rtmp://') and 'live=1' not in src:
        src += ' live=1'
    cmd = ['ffmpeg', '-y'] + tmp_input_options + ['-i', src] + \
        tmp_output_options + ['-f', 'wav', '-map_metadata', '-1', tmp_fn]
    tricks.retry(
            retry_times, tricks.run_cmd_to_generate_files, cmd,
            [tmp_fn], poll_interval=1, timeout=timeout)
    os.rename(tmp_fn, fn)


def main():
    # set up argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('file', help='file to analyze')
    parser.add_argument('--debug', action='store_true',
                        help='set log level to debug (default is info)')
    args = parser.parse_args()

    # set up logging
    log_format = '[%(levelname)s]-%(funcName)s: %(message)s --- %(asctime)s'
    log_formatter = logging.Formatter(log_format)
    logstream_handler = logging.StreamHandler()
    logstream_handler.setFormatter(log_formatter)
    if args.debug:
        logstream_handler.setLevel(logging.DEBUG)
    else:
        logstream_handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logstream_handler)
    logger.info('-' * 40 + '<%s>' + '-' * 40, time.asctime())
    logger.debug('Arguments: %s', args)

    if os.path.isfile(args.file):
        try:
            wave_file = WavFile(args.file)
            wave_file.check_wave_file(check_loudness=True, check_volume=True)
            logger.info(str(wave_file))
        except:
            logger.warning(traceback.format_exc())


if __name__ == '__main__':
    main()
