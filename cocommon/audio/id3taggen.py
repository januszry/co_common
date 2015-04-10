"""
A Simple TextOnly ID3Tag (v2.4.0) Generator
"""

import struct
import functools

import hexdump

major_version = 4
minor_version = 0
encoding_dict = {'iso-8859-1': 0, 'utf-16': 1, 'utf-16be': 2, 'utf-8': 3}


class ID3Tag(object):

    def __init__(self, flag=0x00):
        self._flag = flag
        self._frames = []

    def __str__(self):
        return hexdump.hexdump(self.tag, 'return')

    @property
    def size(self):
        return sum(map(lambda x: len(x.frame), self._frames))

    @property
    def header(self):
        return b'ID3' + \
            struct.pack('>b', major_version) + \
            struct.pack('>b', minor_version) + \
            struct.pack('>b', self._flag) + \
            struct.pack('>i', self.size)

    @property
    def tag(self):
        return self.header + functools.reduce(
                lambda x, y: x + y, map(lambda z: z.frame, self._frames), b'')

    def add_frame(self, frame_id, desc, value, encoding='utf-8', flag=0x0000):
        self._frames.append(ID3Frame(frame_id, desc, value, encoding, flag))

    def write(self, fn):
        with open(fn, 'wb') as f:
            f.write(self.tag)


class ID3Frame(object):

    def __init__(self, frame_id, desc, value,
                 encoding='utf-8', flag=0x0000):
        self._frame_id = frame_id
        self._desc = desc
        self._value = value
        self._encoding = encoding
        self._flag = flag

    def __str__(self):
        return hexdump.hexdump(self.body, 'return')

    @property
    def header(self):
        return self._frame_id.encode('utf-8') + \
            struct.pack('>i', len(self.payload)) + \
            struct.pack('>h', self._flag)

    @property
    def payload(self):
        return struct.pack('>b', encoding_dict[self._encoding]) + \
                '{desc}\0{value}\0'.format(
                desc=self._desc, value=self._value).encode(self._encoding)

    @property
    def frame(self):
        return self.header + self.payload
