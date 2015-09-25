#!/usr/bin/env python3

import os
import time
import logging
import logging.handlers


def config_log(log_dir=None, log_file=None, log_level='INFO',
               rotate=True, back_count=7, name="",
               enable_stream_handler=True,
               multithreading=False, multiprocessing=False,
               log_format=None):
    """Config a default logger.

    Will always create log files rotated by day.

    :param log_dir: log directory.
        If None, current dir
    :param log_file: basename of log file under log_dir.
        If None, no logging to file
    :param log_level: DEBUG | INFO | WARNING | ERROR | CRITICAL
    :param rotate: boolean to enable log rotation
    :param back_count: number of rotated logs to keep
    :param name: logger name space
    :param enable_stream_handler: if True, add StreamHandler
    :param multithreading: add threadId and threadName in log format
    :param multiprocessing: add processId and processName in log format
    :param log_format: if not None, use this format rather than default format
    """

    if log_format is None:
        log_format = '[%(levelname)s]'
        if multithreading:
            log_format += '<t%(thread)d - %(threadName)s>'
        if multiprocessing:
            log_format += '<p%(process)d - %(processName)s>'
        log_format += '<%(module)s>-%(funcName)s: %(message)s --- %(asctime)s'
        log_formatter = logging.Formatter(log_format)

    if log_dir is None:
        log_dir = '.'

    if log_file is not None:
        log_file = os.path.join(log_dir, log_file)
        if rotate:
            loghandler_file = logging.handlers.TimedRotatingFileHandler(
                log_file, when='midnight', interval=1, backupCount=back_count)
        else:
            loghandler_file = logging.FileHandler(log_file)

        loghandler_file.setFormatter(log_formatter)
        loghandler_file.setLevel(getattr(logging, log_level.upper(), None))

    if enable_stream_handler:
        loghandler_stream = logging.StreamHandler()
        loghandler_stream.setFormatter(log_formatter)
        loghandler_stream.setLevel(logging.DEBUG)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if log_file is not None:
        logger.addHandler(loghandler_file)
    if enable_stream_handler:
        logger.addHandler(loghandler_stream)

    return logger


def add_one_time_file_handler(logger, log_dir, log_file, log_level='INFO'):
    """Add a file handler to logger.

    The log file created is not rotated

    :param logger: the logger to add handler to
    :param log_dir: log directory
    :param log_file: basename of log file under log_dir
    :param log_level: DEBUG | INFO | WARNING | ERROR | CRITICAL
    """
    log_format = '[%(levelname)s]'
    log_format += '<%(module)s>-%(funcName)s: %(message)s --- %(asctime)s'
    log_formatter = logging.Formatter(log_format)
    new_handler = logging.FileHandler(os.path.join(log_dir, log_file))
    new_handler.setFormatter(log_formatter)
    new_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(new_handler)


if __name__ == '__main__':
    # set up argparse
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-l', '--log_level', default='INFO', help='log level')
    args = parser.parse_args()

    config_log('.', 'sample.log', args.log_level)

    logger = logging.getLogger(__name__)
    logger.info('-' * 40 + '<%s>' + '-' * 40, time.asctime())
    logger.debug(args)
