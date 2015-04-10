"""
A Simple TextOnly ID3Tag (v2.4.0) Generator
"""

import struct
import functools
import os

import hexdump

major_version = 4
minor_version = 0
encoding_dict = {'iso-8859-1': 0, 'utf-16': 1, 'utf-16be': 2, 'utf-8': 3}


class ID3Tag(object):
    """ID3Tag Generator."""

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
        """Add a new ID3Frame to this ID3Tag.

        :param: frame_id: Frame ID like TXXX
        :param: desc: description
        :param: value: value
        :param: encoding: utf-8 | utf-16 | utf-16be | iso-8859-1
        :param: flag: 16bit flag"""
        self._frames.append(ID3Frame(frame_id, desc, value, encoding, flag))

    def write(self, fn):
        """Write to a binary file only containing ID3Tag."""
        with open(fn, 'wb') as f:
            f.write(self.tag)

    def add_to_adts_file(self, fn, new_fn=None):
        """Add ID3v2 tag to ADTS file.

        Note that ADTS files actually do not support metadata,
        thus this may produce problematic files.

        Note that this function manipulates binary directly,
        file already containing tags should not be provided as input."""
        add_id3tag_to_adts(fn, tag=self.tag, output_adts_file=new_fn)


class ID3Frame(object):
    """An ID3v2 Frame."""

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


def add_id3tag_to_adts(adts_file, output_adts_file=None,
                       tag=None, tag_file=None):
    """Add ID3v2 tag to ADTS file.

    Note that ADTS files actually do not support metadata,
    thus this may produce problematic files.

    Note that this function manipulates binary directly,
    file already containing tags should not be provided as input."""
    DROP_FIRST_N_FRAMES = 2
    with open(adts_file, 'rb') as f:
        origin = f.read()

    if not tag and (not tag_file or not os.path.isfile(tag_file)):
        raise Exception("Please provide at least one of tag and tag_file")

    if not tag:
        with open(tag_file, 'rb') as f:
            tag = f.read()

    index = 0
    for i in range(DROP_FIRST_N_FRAMES):
        index = origin.find(b'\xff\xf1', index + 1)

    if output_adts_file is None:
        output_adts_file = adts_file + '.tagged'
    with open(output_adts_file, 'wb') as f:
        f.write(origin[:index])
        f.write(tag)
        f.write(origin[index:])


def remove_id3tag_from_adts(adts_file, output_adts_file=None):
    raise Exception("Unimplemented")
