#! /usr/bin/env python3
# coding=utf-8

"""austorage.py: populate audio files on cloud storage."""

import os.path
import pprint
import time
from oss import oss_api
from oss import oss_xml_handler

# Work around for a bug in qiniu SDK, which create httplib.HTTPConnection()
# without specifying a timeout and sometimes blocked in getresponse()
# infinitely.
import socket
if not socket.getdefaulttimeout():
    socket.setdefaulttimeout(30)

BigFileSize = 1024 * 1024 * 40


class Item(object):

    def __init__(self):
        self.path = None
        self.size = None
        self.type = None
        self.modifiedTime = None

    def __str__(self):
        return pprint.pformat(vars(self))


class Oss(object):

    """Storage Manager for Ali Oss Service"""

    batch_keys_max = 1000
    batch_prefixes_max = 10

    def __init__(self, **kargs):
        self.bucket = kargs["bucket"]
        self.host = kargs.get("host", "oss-internal.aliyuncs.com")
        self.access_id = kargs["access_id"]
        self.access_key = kargs["access_key"]
        self.oss = oss_api.OssAPI(self.host, self.access_id, self.access_key)

    def exists(self, key):
        """Check if file exists on OSS.

        :param key: remote file name"""
        ret = self.oss.head_object(self.bucket, key)
        if ret.status // 100 == 2:
            return True
        else:
            return False

    def info(self, key):
        """Get info of remote file.

        :param key: remote file name"""
        ret = self.oss.head_object(self.bucket, key)
        if ret.status // 100 != 2:
            return None
        item = Item()
        item.path = key
        item.size = int(ret.getheader('content-length'))
        item.type = ret.getheader('content-type')
        item.modifiedTime = int(
            time.mktime(
                time.strptime(
                    ret.getheader(
                        'last-modified'), "%a, %d %b %Y %H:%M:%S GMT")))
        return item

    def upload(self, filename, key=None,
               overwrite=True, content_type='', headers=None):
        """Upload local file to OSS.

        :param filename: local file name
        :param key: remote file name
        :param overwrite: overwrite remote file if exists
        :param content_type: MIME Type in HTTP header
        :param headers: additional http headers"""
        key = filename if not key else key

        if not overwrite:
            if self.exists(key):
                raise Exception(key + ' already exists.')
        isBigFile = os.path.getsize(filename) > BigFileSize
        if isBigFile:
            res = self.oss.multi_upload_file(self.bucket, key, filename)
        else:
            res = self.oss.put_object_from_file(
                    self.bucket, key, filename, content_type, headers)
        if res.status // 100 == 2:
            return True
        else:
            return False

    def download(self, key, filename):
        """Download file from OSS.

        :param filename: local file name
        :param key: remote file name"""
        info = self.info(key)
        if not info:
            raise Exception("File {} not exists".format(key))
        self.oss.get_object_to_file(self.bucket, key, filename)
        if not os.path.isfile(filename) or \
                os.path.getsize(filename) != info.size:
            raise Exception("Download {} error".format(key))
        return True

    def delete(self, key):
        """Delete remote file.

        :param key: remote file name"""
        res = self.oss.delete_object(self.bucket, key)
        if res.status // 100 == 2:
            return True
        else:
            return False

    def batch_delete(self, keys):
        """Batch delete remote files.

        Note that OSS only supports deleting at most 1000 keys in one request,
        so if len(keys) is longer than 1000,
        deletion will be completed in several requests.

        :param keys: remote file name list."""
        start = 0
        while start < len(keys):
            res = self.oss.batch_delete_objects(
                    self.bucket, keys[start: start + self.batch_keys_max])
            if not res:
                return False
            start += self.batch_keys_max
        return True

    def get_common_prefix(self, prefix, delimiter, timeout=30):
        """Get all common prefixes.

        with <prefix> as prefix, and ends with <delimiter> (one char)"""
        prefixes = []
        marker = ''
        while True:
            res = self.oss.get_bucket(self.bucket, prefix, marker, delimiter,
                                      str(self.batch_prefixes_max),
                                      timeout=timeout)
            if res.status != 200:
                raise Exception('Get bucket failed: {}'.format(res.reason))
            hh = oss_xml_handler.GetBucketXml(res.read())
            (fl, pl) = hh.list()
            prefixes.extend(pl)
            if hh.is_truncated:
                marker = hh.nextmarker
            else:
                break
        return prefixes

    def get_common_prefix_paged(self, prefix, delimiter,
                                page_size=None, timeout=30):
        """Get paged common prefixes.

        with <prefix> as prefix, and ends with <delimiter> (one char)"""
        marker = ''
        if not page_size:
            page_size = self.batch_prefixes_max
        while True:
            res = self.oss.get_bucket(self.bucket, prefix, marker, delimiter,
                                      str(page_size), timeout=timeout)
            if res.status != 200:
                raise Exception('Get bucket failed: {}'.format(res.reason))
            hh = oss_xml_handler.GetBucketXml(res.read())
            (fl, pl) = hh.list()
            yield pl
            if hh.is_truncated:
                marker = hh.nextmarker
            else:
                break

    def list(self, prefix):
        """Get full list with specified prefix.

        Note this might be very slow. If you need paged list, use ilist."""
        files = []
        marker = ''
        delimiter = ''
        while True:
            res = self.oss.get_bucket(self.bucket, prefix, marker, delimiter,
                                      str(self.batch_keys_max))
            if res.status != 200:
                raise Exception('Get bucket failed: {}'.format(res.reason))
            hh = oss_xml_handler.GetBucketXml(res.read())
            (fl, pl) = hh.list()
            files.extend(fl)
            if hh.is_truncated:
                marker = hh.nextmarker
            else:
                break
        return files

    def list_paged(self, prefix, page_size=None):
        """Get paged list with specified prefix.

        Generator to return a page of length <page_size>
        until full list is read.

        :param page_size: if not specified, assigned batch_keys_max."""
        marker = ''
        delimiter = ''
        if not page_size:
            page_size = self.batch_keys_max
        while True:
            res = self.oss.get_bucket(self.bucket, prefix, marker, delimiter,
                                      str(page_size))
            if res.status != 200:
                raise Exception('Get bucket failed: {}'.format(res.reason))
            hh = oss_xml_handler.GetBucketXml(res.read())
            (fl, pl) = hh.list()
            yield fl
            if hh.is_truncated:
                marker = hh.nextmarker
            else:
                break
