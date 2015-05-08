#! /usr/bin/env python3
# coding=utf-8
# @author Coppola Zeng

"""
A set of common tools
"""

import os
import argparse
import subprocess
import logging
import time
import hashlib
import glob
import tempfile
import pickle

import pexpect
import requests
import paramiko

from . import rst_gen
from .compat import urlparse, get_urlparsable_string


SUBPROCESS_TIMEOUT_DEFAULT = 5
SUBPROCESS_POLLING_RATE_DEFAULT = 0.5
FILE_GENERATING_TIMEOUT_DEFAULT = 30
TIMESTR_FORMAT_DEFAULT = '%Y%m%d_%H%M%S'
TIMESTR_FORMAT_API = '%yM%mD%dh%Hm%Ms%S'
TIMESTR_FORMAT_FULL = '%Y-%m-%d %H:%M:%S'
DATESTR_FORMAT = '%Y%m%d'
DATESTR_FORMAT_FULL = '%Y-%m-%d'
NULL_FILE = '/dev/null'


def request_url_and_cache_result(url, method='GET', data=None,
                                 cache_fn=None, cache_dir='/tmp',
                                 expire_time=86400, flush=False):
    """Request an URL and cache the result in file, return the result.

    :param url: The url to request
    :param method: HTTP method, get | post
    :param data: Dictionary, bytes, or file-like object to send
    :param cache_fn: The name of the file to cache in, md5hash if not specified
    :param cache_dir: The dir to save the cache file name
    :param expire_time: Cache expiration time
    :param flush: Force flushing cache"""
    logger = logging.getLogger(__name__)

    if method not in ['GET', 'POST']:
        logger.warning('Only support GET and POST here')
        return

    url = url_fix(url)

    if not isinstance(url, str):
        logger.error("Wrong API URL: %s", url)
        return

    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)

    if not cache_fn:
        m = hashlib.md5()
        m.update((url + str(method) + str(data)).encode('utf-8'))
        cache_fn = os.path.join(cache_dir, m.hexdigest())
    if not flush and os.path.isfile(cache_fn) and \
            time.time() - os.path.getmtime(cache_fn) <= expire_time:
        try:
            with open(cache_fn, 'rb') as f:
                data = pickle.load(f)
            return data
        except pickle.UnpicklingError:
            logger.warning('Corrupt cache content, will refetch')
            os.remove(cache_fn)
    elif os.path.isfile(cache_fn):
        os.remove(cache_fn)

    start_time = time.time()
    if data:
        ret = getattr(requests, method.lower())(url, data)
    else:
        ret = getattr(requests, method.lower())(url)
        ret = requests.get(url)
    ret.close()
    logger.info("Repuesting %s took time % seconds",
                url, time.time() - start_time)
    if ret.status_code == 200:
        data = ret.text
        tmp_cache_fn = '{}.{}'.format(cache_fn, int(time.time()))
        with open(tmp_cache_fn, 'wb') as f:
            pickle.dump(data, f)
        os.rename(tmp_cache_fn, cache_fn)
        return data
    else:
        logger.warning("Requesting api %s error", url)


def is_ascii(s):
    """Check if input is ASCII string.

    >>> is_ascii("sdfsfd")
    True

    >>> is_ascii("我们")
    False
    """

    if isinstance(s, str):
        s = s.encode('utf-8')
    if not isinstance(s, bytes):
        return False
    return all(c < 128 for c in s)


def url_fix(s):
    """Get a valid URL.

    Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.  This
    function can fix some of the problems in a similar way browsers
    handle data entered by the user:

    >>> url_fix('http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    >>> url_fix('mmst://60.21.157.2/丹东电台都市频率')
    'mmst://60.21.157.2/%E4%B8%B9%E4%B8%9C%E7%94%B5%E5%8F%B0%E9%83%BD%E5%B8%82%E9%A2%91%E7%8E%87'
    """
    s = get_urlparsable_string(s)
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urlparse.quote(path, '/%')
    qs = urlparse.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


def do_host(
        host,
        username,
        password,
        commands=[],
        log_dir='.',
        expect_done_sign=']#',
        timeout=30):
    """Run a list of commands on a host."""
    logger = logging.getLogger(__name__)
    logger.info('ssh to %s:%s@%s', username, password, host)
    child = pexpect.spawn(
        'ssh {username}@{host}'.format(username=username, host=host))
    f = open(os.path.join(log_dir, '{}.log').format(host), 'w')
    child.logfile = f.buffer

    i = child.expect(
        [expect_done_sign, '(yes/no)', 'assword:'], timeout=timeout)
    if i == 0:
        logger.info('Certificated machine %s', host)
    elif i == 1:
        logger.info('First access to machine %s', host)
        child.sendline('yes')
        child.expect('assword:', timeout=timeout)
        time.sleep(0.7)
        child.sendline(password)
    elif i == 2:
        logger.info('Password certification at machine %s', host)
        time.sleep(0.7)
        child.sendline(password)
    child.expect(expect_done_sign, timeout=timeout)
    for cmd in commands:
        logger.info('Sending command %s', cmd)
        child.sendline(cmd)
        child.expect(expect_done_sign, timeout=timeout)
    child.sendline('exit')
    child.expect(pexpect.EOF)
    f.close()


def do_host_paramiko(
        host,
        username,
        password,
        commands=[],
        log_dir='.',
        log_file=None,
        port=22,
        timeout=30):
    """Run a list of commands on a remote host with paramiko."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, username, password)
    if log_file is None:
        log_file = '{}.log'.format(host)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    with open(os.path.join(log_dir, log_file), 'w') as f:
        r = rst_gen.RestructuredTextGenerator()
        for command in commands:
            _, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            f.write
            f.write(r.section_header(0, '{} - {}'.format(
                command, seconds_to_timestr(time.time()))))
            f.write(r.section_header(1, 'stdout'))
            lines = stdout.readlines()
            if lines:
                lines = [i[:-1] for i in lines]
                f.write(r.source_code(*lines))
            f.write(r.section_header(1, 'stderr'))
            lines = stderr.readlines()
            if lines:
                lines = [i[:-1] for i in lines]
                f.write(r.source_code(*lines))
            f.write(r.end_of_block())


def retry(retry_times, f, *args, **kwargs):
    """Try calling function f several times until f returned normally."""
    # logger = logging.getLogger(__name__)
    te = None
    while retry_times:
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # logger.warning(traceback.format_exc())
            te = e
            retry_times -= 1
    if te:
        raise te


def req_url_with_auth(url, username=None, password=None, retry_times=5):
    """Request a URL several times until returned 200.

    >>> req_url_with_auth('http://www.163.com/')
    <Response [200]>

    >>> req_url_with_auth('http://121.199.18.53/live.html')
    <Response [200]>"""
    logger = logging.getLogger(__name__)
    e = None
    while retry_times:
        try:
            if username and password:
                res = requests.get(
                    url, auth=requests.auth.HTTPBasicAuth(username, password),
                    stream=True)
            else:
                res = requests.get(url, stream=True)
            if res.status_code / 100 == 2:
                return res
            raise Exception(
                'Requesting URL [{}] returned [{} - {}]'.format(
                    url, res.status_code, res.reason))
        except Exception as te:
            logger.warn(te)
            e = te
            retry_times -= 1
    if e:
        raise e


def seconds_to_timestr(seconds=None, fmt=TIMESTR_FORMAT_DEFAULT):
    """Convert unix time to time in str.

    >>> seconds_to_timestr(1395644416)
    '20140324_150016'

    >>> seconds_to_timestr(1395644416, TIMESTR_FORMAT_API)
    '14M03D24h15m00s16'

    >>> seconds_to_timestr(1395644416, TIMESTR_FORMAT_FULL)
    '2014-03-24 15:00:16'
    """
    return time.strftime(fmt, time.localtime(seconds))


def timestr_to_seconds(timestr, fmt=TIMESTR_FORMAT_DEFAULT):
    """Convert time in str to unix time.

    >>> timestr_to_seconds('20140324_150016')
    1395644416

    >>> timestr_to_seconds('14M03D24h15m00s16', TIMESTR_FORMAT_API)
    1395644416

    >>> timestr_to_seconds('2014-03-24 15:00:16', TIMESTR_FORMAT_FULL)
    1395644416
    """
    return int(time.mktime(time.strptime(timestr, fmt)))


def seconds_to_date_tuple(seconds=None):
    """Convert unix time in seconds to date tuple in (year, month, day).

    >>> seconds_to_date_tuple(1397097766)
    (2014, 4, 10)
    """
    t = time.localtime(seconds)
    return (t.tm_year, t.tm_mon, t.tm_mday)


def get_start_second_of_day_of_given_second(seconds=None):
    return timestr_to_seconds(seconds_to_timestr(seconds, DATESTR_FORMAT_FULL),
                              DATESTR_FORMAT_FULL)


def date_tuple_to_seconds(date_tuple):
    """Convert date tuple in (year, month, day) to unix time in seconds.

    >>> date_tuple_to_seconds((2013, 4, 10))
    1365523200
    """
    return int(time.mktime(time.strptime('{}-{}-{}'.format(
        date_tuple[0], date_tuple[1], date_tuple[2]), '%Y-%m-%d')))


def get_date_tuple_list(start_date_tuple, end_date_tuple):
    """Get a list of date tuple from start to end.

    >>> get_date_tuple_list((2014, 2, 25), (2014, 3, 1))
    [(2014, 2, 25), (2014, 2, 26), (2014, 2, 27), (2014, 2, 28), (2014, 3, 1)]
    """
    start_seconds = date_tuple_to_seconds(start_date_tuple)
    end_seconds = date_tuple_to_seconds(end_date_tuple)
    result = []
    while start_seconds <= end_seconds:
        result.append(seconds_to_date_tuple(start_seconds))
        start_seconds += 86400
    return result


def get_str_md5(s):
    """Calculate HEX md5 of str.

    >>> get_str_md5('I love 蜻蜓.FM')
    '55919339f43e8afaf9fd5287bc07a591'
    """
    if isinstance(s, str):
        s = s.encode('utf-8')
    m = hashlib.md5()
    m.update(s)
    return m.hexdigest()


def subprocess_check_output(args, timeout=SUBPROCESS_TIMEOUT_DEFAULT,
                            polling_rate=SUBPROCESS_POLLING_RATE_DEFAULT,
                            output_device=0):
    """Execute a subprocess with a watchdog.

    Return the output if return code is zero."""
    output = None
    return_code = None

    files = [tempfile.TemporaryFile(), tempfile.TemporaryFile()]

    subp = subprocess.Popen(
        args, stdout=files[0], stderr=files[1], universal_newlines=True)

    t = 0
    while t < timeout and subp.poll() is None:
        t += polling_rate
        time.sleep(polling_rate)

    if subp.poll() is not None:
        return_code = subp.poll()

        try:
            files[output_device].seek(0)
            output = files[output_device].read().strip()
        except UnicodeDecodeError as e:
            output = e.args[1].decode(e.args[0], 'replace')

        for tf in files:
            tf.close()

        if return_code != 0:
            raise subprocess.CalledProcessError(
                return_code, ' '.join(args), output)
        else:
            return output
    else:
        for tf in files:
            tf.close()
        subp.kill()
        raise Exception('Subprocess timeout: {}'.format(args))


def check_file_generation_timeout(fn, start_time,
                                  timeout=FILE_GENERATING_TIMEOUT_DEFAULT):
    """Check if generates no new data in timeout in seconds.

    * If file is not created for <timeout>, timeout
    * If file is created but not updated for <timeout>, timeout
    """
    logger = logging.getLogger(__name__)
    try:
        if not os.path.isfile(fn) and time.time() - start_time > timeout:
            logger.info('%s not generated in %s seconds, timeout', fn, timeout)
            return True
        elif not os.path.isfile(fn):
            return False
        elif time.time() - os.path.getmtime(fn) > timeout:
            logger.info('%s not updated for %s seconds, timeout', fn, timeout)
            return True
        return False
    except Exception:
        # May be file is moved or removed after successful generation
        return False


def run_cmd_to_generate_files(cmd, fns, poll_interval=1,
                              timeout=FILE_GENERATING_TIMEOUT_DEFAULT):
    """Run a cmd to generate files.

    Will check first file in iterable fns to see if file is updated recently
    """
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info(' '.join(cmd))

    null_f = open(NULL_FILE, 'w')

    subp = subprocess.Popen(
        cmd, stdout=null_f, stderr=null_f)
    for fn in fns:
        if os.path.isfile(fn):
            os.remove(fn)
    fn = fns[0]
    while subp.poll() is None:
        is_timeout = check_file_generation_timeout(fn, start_time, timeout)
        if is_timeout:
            logger.info('Generating %s timeout, kill', fns)
            while subp.poll() is None:
                subp.kill()
            for fn in fns:
                if os.path.isfile(fn):
                    os.remove(fn)
            raise Exception('Timeout')
        time.sleep(poll_interval)
    if subp.returncode == 0:
        return 'OK'
    else:
        raise Exception('Generate Error', subp.returncode, cmd)


def get_last_n_files(target_dir, pattern, n=1, sort_key='name'):
    """Get last n files with specified pattern in specified dir.

    :param target_dir: target dir
    :param pattern: wildcard pattern
    :param n: max number of files to return
    :param sort_key: name or mtime"""
    logger = logging.getLogger(__name__)
    tmp = glob.glob(os.path.join(target_dir, pattern))
    if not tmp:
        logger.warning('No file in %s fits pattern %s', target_dir, pattern)
        return
    if sort_key == 'name':
        tmp.sort()
    elif sort_key == 'mtime':
        tmp.sort(key=lambda x: os.path.getmtime(x))
    else:
        logger.warning('Unknown sort key %s', sort_key)
        return
    return tmp[-n:]


def remove_old_files_like(pat, old_bound=7200):
    """Remove old files older than bound (in seconds)"""
    logger = logging.getLogger(__name__)
    files = glob.glob(pat)
    for i in files:
        if os.path.isfile(i) and time.time() - os.path.getmtime(i) > old_bound:
            os.remove(i)
            logger.warn('Removed old file %s', i)


def string_list(s):
    """Type: list of string delimitered by double semi-colon.

    >>> string_list("sldjfl;;woeruwoer;;xcv   xvcxv")
    ['sldjfl', 'woeruwoer', 'xcv   xvcxv']
    """
    return s.split(';;')


if __name__ == '__main__':
    # set up argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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

    import doctest
    doctest.testmod()
