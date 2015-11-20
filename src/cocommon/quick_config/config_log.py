#!/usr/bin/env python3

import os
import time
import logging
import logging.handlers

import fluent.handler
import raven.handlers.logging


def config_log(log_dir=None, log_file=None, log_level='INFO',
               rotate=True, back_count=7, name=None,
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
    elif not os.path.isdir(log_dir):
        os.makedirs(log_dir)

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
    # cleanup old handlers
    for h in logger.handlers:
        h.close()
    logger.handlers = []
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
    return logger


class HTTPHandlerWithExtraMessage(logging.handlers.HTTPHandler):
    _extra_message = None

    def set_extra_message(self, msg):
        self._extra_message = msg

    def mapLogRecord(self, record):
        record.extra_message = self._extra_message
        return record.__dict__


def add_one_time_http_handler(
        logger, remote_http_server, remote_http_path, extra_message=None,
        method='POST', log_level='INFO'):
    """Add a http handler to logger.

    :param logger: the logger to add handler to
    :param remote_http_server: host:port without protocol
    :param remote_http_path: path like '/'
    :param logger: logger to add new handler to
    :param extra_message: extra message to send with every log record
    :param log_level: DEBUG | INFO | WARNING | ERROR | CRITICAL
    """

    new_handler = HTTPHandlerWithExtraMessage(
        remote_http_server, remote_http_path, method)
    new_handler.set_extra_message(extra_message)
    new_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(new_handler)
    return logger


def add_fluent_logger_handler(
        logger, tag, host='127.0.0.1', port=24224,
        extra_message=None, log_level='INFO'):
    """Add a fluent-loghandler to logger.

    :param logger: the logger to add handler to
    :param tag: tag of fluent-logger
    :param host: host of fluent-logger server
    :param port: port number of fluent-logger server
    :param extra_message: extra message to send with log message
        can be str or dict
    :param log_level: DEBUG | INFO | WARNING | ERROR | CRITICAL
    """
    custom_format = {
        'host': '%(hostname)s',
        'level': '%(levelname)s',
        'where': '%(module)s.%(funcName)s',
        'stack_trace': '%(exc_text)s',
        'formatted_message': '%(message)s',
        'full_message':
        '[%(levelname)s] <%(module)s>.%(funcName)s'
        ' \'%(message)s\' [%(asctime)s]',
    }
    if isinstance(extra_message, dict):
        custom_format.update(extra_message)
    else:
        custom_format['extra_message'] = str(extra_message)
    h = fluent.handler.FluentHandler(tag, host=host, port=port)
    formatter = fluent.handler.FluentRecordFormatter(custom_format)
    h.setFormatter(formatter)
    h.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(h)
    return logger


def add_sentry_handler(
        logger, sentry_dsn, log_level='WARNING'):
    """Add a sentry-loghandler to logger.

    :param logger: the logger to add handler to
    :param sentry_dsn: Sentry server DSN, see in Project -> Settings
    :param log_level: DEBUG | INFO | WARNING | ERROR | CRITICAL
    """
    h = raven.handlers.logging.SentryHandler(sentry_dsn)
    h.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(h)
    return logger


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
