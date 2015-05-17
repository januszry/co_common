#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# @author Ruoyu Zeng

""" This module access the api server and get all the URLs of streams. """

import time
import os
import pickle
import requests

import ujson

from . import tricks


class ApiAccess(object):

    def __init__(
            self,
            api_res_list, api_find_resource_by_id,
            api_category_list, api_channel_list_under_category,
            resource_data_cache, channel_data_cache,
            expire_time=86400):
        self._api_res_list = api_res_list
        self._api_find_resource_by_id = api_find_resource_by_id
        self._api_category_list = api_category_list
        self._api_channel_list_under_category = api_channel_list_under_category
        self._resource_data_cache = resource_data_cache
        self._channel_data_cache = channel_data_cache

        self._expire_time = expire_time

        self._resource_list = None
        self._channel_dict = None

    def get_resource_list(self, exclude_conditions=[],
                          flush=False, get_channel_info=False):

        """Get resource list from API.

        Use _api_res_list to get a complete resource list.
        The result is cached until expire_time is reached.
        :param exclude_conditions: tuple (key, value)"""

        if flush:
            expire_time = 0
        else:
            expire_time = 86400
        resource_list = ujson.loads(
            tricks.request_url_and_cache_result(
                self._api_res_list,
                cache_fn=self._resource_data_cache,
                expire_time=expire_time))['data']

        def valid(resource):
            for i in exclude_conditions:
                if i[0] in resource and i[1] == resource[i[0]]:
                    return False
            return True
        # filter resource_list with exclude_conditions
        resource_list = list(filter(valid, resource_list))

        if get_channel_info:
            for resource in resource_list:
                res_id = str(resource['res_id'])
                try:
                    channel = self.get_channel_dict()[res_id]
                    resource['catname'] = channel['catname']
                    resource['parentcatname'] = channel['parentcatname']
                    resource['channel_id'] = channel['id']
                except KeyError:
                    resource['catname'] = 'Unknown'
                    resource['parentcatname'] = 'Unknown'
                    resource['channel_id'] = 'Unknown'
        return list(resource_list)

    def find_resource_by_id(self, res_id, get_channel_info=True):
        ret = requests.get(
            self._api_find_resource_by_id.format(res_id=res_id))
        if ret.status_code == 200:
            resource = ret.json()['data']
        else:
            return None

        try:
            channel = self.get_channel_dict()[str(res_id)]
            resource['catname'] = channel['catname']
            resource['parentcatname'] = channel['parentcatname']
            resource['channel_id'] = channel['id']
        except KeyError:
            resource['catname'] = 'Unknown'
            resource['parentcatname'] = 'Unknown'
            resource['channel_id'] = 'Unknown'
        return resource

    def get_channel_dict(
            self, status_list=['pass', 'review', 'reject'], flush=False):
        if not flush:
            if self._channel_dict is not None:
                return self._channel_dict
            if os.path.isfile(self._channel_data_cache) and \
                    time.time() - os.path.getmtime(
                        self._channel_data_cache) < self._expire_time:
                    try:
                        with open(self._channel_data_cache, 'rb') as f:
                            self._channel_dict = pickle.load(f)
                        return self._channel_dict
                    except:
                        os.remove(self._channel_data_cache)

        channel_dict = {}
        category_list = requests.get(self._api_category_list).json()['data']
        for i in category_list:
            # TODO: category is given in a list of dimensions: 地区 国家 类型
            if i['name'] == '地区':
                parentcatname = '国内'
            elif i['name'] == '国家':
                parentcatname = '国外'
            elif i['name'] == '类型':
                parentcatname = '其他'
            else:
                continue
            for j in i['values']:
                category_id = j['id']
                for status in status_list:
                    tmp_channel_list = requests.get(
                        self._api_channel_list_under_category.format(
                            status=status,
                            category_id=category_id)).json()['data']
                    for channel in tmp_channel_list:
                        channel['catname'] = j['name']
                        channel['parentcatname'] = parentcatname
                        channel['status'] = status
                        res_id = str(channel['res_id'])
                        if res_id not in channel_dict:
                            channel_dict[res_id] = channel
        self._channel_dict = channel_dict
        if self._channel_data_cache:
            with open(self._channel_data_cache, 'wb') as f:
                pickle.dump(self._channel_dict, f)
        return self._channel_dict
