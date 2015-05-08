#! /usr/bin/env python3
# @author Rui Lin and Ruoyu Zeng

"""
Collect machine status
Can only be used on linux
"""

import logging
import logging.handlers
import time
import pprint
import traceback

from . import sysstat


def get_avg_by_sum(buf, div_factor=1):
    avg = {}
    if len(buf) > 1:
        div_factor *= (len(buf) - 1)

        sum0 = buf[0]
        sum1 = buf[-1]
        for key in sum0:
            avg[key] = (sum1[key] - sum0[key]) / div_factor
    return avg


def get_avg(buf):
    """buf is a list of dict with same keys"""
    avg = {}
    if len(buf) > 0:
        avg = buf[0].copy()

        for ele in buf[1:]:
            for key in avg:
                avg[key] += ele[key]

        for key in avg:
            avg[key] /= len(buf)

    return avg


def get_percent(adict):
    s = sum(adict.values())
    return {k: round(adict[k] * 100.0 / s, 2) for k in adict}


class SysMon(object):

    """A system info monitor.

    :param output: a dictionary for output as this module
        usually runs in a stand alone thread"""

    def __init__(self, output, update_interval=1):
        """argument output is the place for output"""
        self._logger = logging.getLogger(__name__)
        self._cpu_data = []
        self._mem_data = []
        self._disk_data = {}  # multiple disks
        self._network_data = {}  # multiple interfaces
        self._update_interval = update_interval
        self.output = output

    @staticmethod
    def refresh_stat_buffer(buf, buf_limit, new_data):
        if len(buf) == buf_limit:
            buf.pop(0)
        buf.append(new_data)

    @staticmethod
    def get_ip_address(ifname):
        """Get ip address by interface name

        :param ifname: interface name"""
        return sysstat.get_ip_address(ifname)

    def get_sys_info(self):
        """Get system infomation.

        Consists of CPU, Memory,
        Disk (every disk), Network (every interface)"""

        self.refresh_stat_buffer(self._cpu_data, 15, sysstat.read_cpu_usage())

        self.refresh_stat_buffer(self._mem_data, 1, sysstat.read_mem_usage())

        disk_usage = sysstat.read_disk_usage()
        for k, v in disk_usage.items():
            if k not in self._disk_data:
                self._disk_data[k] = []
            self.refresh_stat_buffer(self._disk_data[k], 1, v)

        network_usage = sysstat.read_network_usage_v2()
        for k, v in network_usage.items():
            if k not in self._network_data:
                self._network_data[k] = []
            self.refresh_stat_buffer(self._network_data[k], 15, v)

        self.output.update({'cpu_info': get_percent(
            get_avg_by_sum(self._cpu_data, self._update_interval)),
            'mem_info': get_avg(self._mem_data),
            'disk_info': {k: get_avg(v)
                          for k, v in self._disk_data.items()},
            'network_info': {k: get_avg_by_sum(
                             v, self._update_interval)
                             for k, v in self._network_data.items()},
        })

        self._logger.info(pprint.pformat(self.output))
        return self.output

    def run(self, exit_event):
        """Run, usually as a stand alone thread

        :param exit_event: threading.Event
        """
        while not exit_event.is_set():
            try:
                self.get_sys_info()
            except:
                self._logger.warning(traceback.format_exc())
            time.sleep(self._update_interval)


def main():
    # configure logging
    log_format = '[%(levelname)s]-%(funcName)s: %(message)s --- %(asctime)s'
    log_formatter = logging.Formatter(log_format)
    logstream_handler = logging.StreamHandler()
    logstream_handler.setFormatter(log_formatter)
    logstream_handler.setLevel(logging.DEBUG)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logstream_handler)

    logger = logging.getLogger(__name__)
    logger.info('\n\n' + '-' * 30 + '<%s>' + '-' * 30, time.asctime())

    output = {}
    sys_mon = SysMon(output)
    import threading
    exit_event = threading.Event()
    sys_mon.run(exit_event)


if __name__ == '__main__':
    main()
