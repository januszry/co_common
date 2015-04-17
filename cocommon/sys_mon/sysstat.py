import subprocess
import socket
import fcntl
import struct


def get_ip_address(ifname):
    """Get ip address by interface name

    :param ifname: interface name"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,
                            struct.pack(
                                '256s',
                                ifname[:15].encode('utf-8')))[20:24])


def read_cpu_usage():
    """CPU usage from /proc/stat.

    http://man7.org/linux/man-pages/man5/proc.5.html"""
    # Example:
    # cpu  71629 16549 132174 573280 15806 666 0 0 0 0
    # cpu0 7377 4326 32179 154633 3787 115 0 0 0 0
    # cpu1 6597 4844 38304 146713 5774 162 0 0 0 0
    # cpu2 22413 3116 26243 147829 2750 273 0 0 0 0
    # cpu3 35240 4262 35445 124103 3493 115 0 0 0 0
    # intr 5266671 16 3084 0 0 0 0 0 0 1 3184 0 0 672518 0 0 0 276 0 0 0 ...
    # ctxt 18558358
    # btime 1400122420
    # processes 4936
    # procs_running 2
    # procs_blocked 0
    # softirq 1291594 70 669951 569 54212 279315 0 3139 139057 1785 143496

    cpu_usage = {}
    with open('/proc/stat', 'r') as f:
        data = f.readline().split()

    cpu_usage['usr'] = int(data[1])
    cpu_usage['nice'] = int(data[2])
    cpu_usage['sys'] = int(data[3])
    cpu_usage['idle'] = int(data[4])
    cpu_usage['iowait'] = int(data[5])
    cpu_usage['irq'] = int(data[6])
    cpu_usage['softirq'] = int(data[7])
    cpu_usage['steal'] = int(data[8])

    return cpu_usage


def read_mem_usage():
    """MEM usage by free."""

    # Example:
    #              total       used       free     shared    buffers     cached
    # Mem:       1017972     930632      87340          0      92860     545564

    mem_usage = {}
    free_output = subprocess.check_output(
        ['free'], universal_newlines=True, close_fds=True)

    data = free_output.splitlines()[1].split()
    mem_usage['total'] = int(data[1])
    mem_usage['used'] = int(data[2])
    mem_usage['free'] = int(data[3])
    mem_usage['buffers'] = int(data[5])
    mem_usage['cached'] = int(data[6])

    return mem_usage


def read_disk_usage():
    """DISK usage by df."""

    # Example:
    # Filesystem     1K-blocks     Used Available Use% Mounted on
    # /dev/xvda1      20903812 13288612   6566728  67% /

    disk_usage = {}
    df_output = subprocess.check_output(
        ['df'], universal_newlines=True, close_fds=True)

    lines = df_output.splitlines()[1:]
    for line in lines:
        data = line.split()
        disk_usage[data[0]] = {
            'total': int(data[1]) >> 10,  # MB
            'used': int(data[2]) >> 10,
            'free': int(data[3]) >> 10
        }

    return disk_usage


def read_network_usage():
    """Network usage from /proc/net/dev."""

    network_usage = {}
    with open('/proc/net/dev', 'r') as f:
        lines = f.readlines()

    for line in lines[2:]:
        iface, stats = line.split(':')
        iface = iface.strip()

        stats = stats.split()
        network_usage.update({
            iface + "_rx": int(stats[0]) >> 7,  # Kb
            iface + "_tx": int(stats[8]) >> 7,
        })

    return network_usage


def read_network_usage_v2():
    """Network usage from /proc/net/dev.

    return a dictionary by key of every interface
    Recommended version."""

    network_usage = {}
    with open('/proc/net/dev', 'r') as f:
        lines = f.readlines()

    for line in lines[2:]:
        iface, stats = line.split(':')
        iface = iface.strip()

        stats = stats.split()
        network_usage[iface] = {
            "rx": int(stats[0]) >> 7,  # Kb
            "tx": int(stats[8]) >> 7
        }

    return network_usage
