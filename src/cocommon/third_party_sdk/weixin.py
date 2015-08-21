#!/usr/bin/env python3

import pprint
import time
import os
import base64
import hashlib

import requests

API_ACCESS_TOKEN = 'https://api.weixin.qq.com/cgi-bin/token' + \
                   '?grant_type=client_credential' + \
                   '&appid={app_id}' + \
                   '&secret={app_secret}'

API_JSAPI_TICKET = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket' + \
                   '?access_token={access_token}' + \
                   '&type=jsapi'

EXPIRE = 6000


class WeiXin(object):

    def __init__(self, app_id, app_secret):
        self._app_id = app_id
        self._app_secret = app_secret
        self._timestamp = None
        self._access_token = None
        self._jsapi_ticket = None
        self._signature = None
        self._nonce_str = None

    def __str__(self):
        return pprint.pformat(vars(self))

    def _get_access_token(self):
        now_time = int(time.time())
        if self._timestamp and self._access_token and \
                now_time - self._timestamp < EXPIRE:
            return self._access_token
        res = requests.get(API_ACCESS_TOKEN.format(
            app_id=self._app_id, app_secret=self._app_secret))
        if res.status_code == 200:
            self._access_token = res.json()['access_token']
            self._timestamp = now_time
            return self._access_token
        raise Exception('{}: {}'.format(res.status_code, res.reason))

    def _get_jsapi_ticket(self):
        if self._timestamp and self._jsapi_ticket and \
                time.time() - self._timestamp < EXPIRE:
            return self._jsapi_ticket
        res = requests.get(API_JSAPI_TICKET.format(
            access_token=self._get_access_token()))
        if res.status_code == 200:
            self._jsapi_ticket = res.json()['ticket']
            return self._jsapi_ticket
        raise Exception('{}: {}'.format(res.status_code, res.reason))

    def _get_nonce_str(self):
        if self._timestamp and self._nonce_str and \
                time.time() - self._timestamp < EXPIRE:
            return self._nonce_str
        self._nonce_str = base64.urlsafe_b64encode(
                os.urandom(10)).decode('utf-8')
        return self._nonce_str

    def _get_signature(self, url):
        jsapi_ticket = self._get_jsapi_ticket()
        nonce_str = self._get_nonce_str()
        timestamp = self._timestamp
        s = 'jsapi_ticket={}&noncestr={}&timestamp={}&url={}'.format(
                jsapi_ticket, nonce_str, timestamp, url)
        return hashlib.sha1(s.encode('utf-8')).hexdigest()

    def get_weixin_config(self, url):
        signature = self._get_signature(url)
        return {'debug': True,
                'appId': self._app_id,
                'timestamp': self._timestamp,
                'nonceStr': self._nonce_str,
                'signature': signature}
