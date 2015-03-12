#! /usr/bin/env python3

"""
String / Object Parsers

     StringParser
        /    \
  XMLParser REParser
      /
 DictParser
    /
JSONParser
"""


import logging
import logging.handlers
import traceback
import pprint
import re

import ujson
import xmltodict
from lxml import etree
from lxml import html


class Parser(object):
    """Parser to extract a list of filtered string from a string."""

    def __init__(self, expr):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._expr = expr

    def __str__(self):
        return pprint.pformat(vars(self))

    def parse(self, s):
        """Should be implemented by subclass"""
        pass


class XMLParser(Parser):

    """Parser to extract a list of xml string from a XML."""

    def __init__(self, xpath_expr):
        super().__init__(xpath_expr)
        self._root_elem = None

    def _get_root_elem(self, xml_str):
        try:
            try:
                if not isinstance(xml_str, bytes):
                    tmp_xml_str = str(xml_str).encode('utf-8')
                self._root_elem = etree.fromstring(tmp_xml_str)
            except etree.XMLSyntaxError:
                self._root_elem = html.fromstring(xml_str)
        except etree.XMLSyntaxError:
            self.logger.error('input is in wrong format: [%s]', xml_str)
            self._root_elem = None

    def _parse(self, xml_str):
        def _get_str_from_xpath_result(elem):
            if isinstance(elem, etree._Element):
                return etree.tounicode(elem).strip()
            elif isinstance(elem, str):
                return elem.strip()
            elif isinstance(elem, bytes):
                return elem.decode('utf-8').strip()
            else:
                return str(elem).strip()
        try:
            self._get_root_elem(xml_str)
            return list(map(
                _get_str_from_xpath_result, self._root_elem.xpath(self._expr)))
        except:
            self.logger.warning(
                'Error parsing [%s]: %s', xml_str, traceback.format_exc())

    def parse(self, xml_str):
        """Parse an XML string with etree.Element.xpath.

        Return a list of XML strings
        To get the text rather than the node,
        use /text() function at the end of text path"""
        return self._parse(xml_str)


class DictParser(XMLParser):

    """Parser to extract a list of string from a dict.

    We're using xpath to parse every structed data,
    so we turn dict into xml."""

    def __init__(self, xpath_str):
        super().__init__(xpath_str)

    def parse(self, data):
        """Parse dict

        :param data: if it is a list, turn it into a dict as {'node': data}

        We turn dict into xml and parse it with etree.Element.xpath
        To get the text rather than the node,
        use /text() function at the end of text path"""

        if isinstance(data, list):
            data = {'nodes': data}
        elif not isinstance(data, dict):
            data = str(data)
        xml_str = xmltodict.unparse({'data': data})
        return self._parse(xml_str)


class JSONParser(DictParser):

    """Parser to extract a list of string from a json.

    We're using xpath to parse every structed data,
    so we turn json into dict further into xml"""

    def __init__(self, xpath_str):
        super().__init__(xpath_str)

    def parse(self, json_str):
        """Parse JSON string.

        We turn json into dict further into xml,
        and parse it with etree.Element.xpath
        To get the text rather than the node,
        use /text() function at the end of text path"""
        try:
            data = ujson.loads(json_str)
        except ValueError:
            self.logger.warning("Invalid JSON string: %s", json_str)
        # a hack to prevent a wrong json with a list in highest level
        return super().parse(data)


class REParser(Parser):

    """Parser to extract a list of string from a string with RE."""

    def __init__(self, regular_expression):
        super().__init__(regular_expression)

    def parse(self, s):
        """Parse a string with re.

        Return a list of strings."""
        return re.findall(self._expr, s)


class PlaylistParser(object):

    """Parser to extract play URL(s) from playlists.

    Please refer to http://gonze.com/playlists/playlist-format-survey.html
    for detailed information."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def parse(self, playlist_content, playlist_type):
        try:
            if isinstance(playlist_content, bytes):
                playlist_content = playlist_content.decode('utf-8')
            if not isinstance(playlist_content, str):
                self.logger.warning(
                    'Wrong playlist_content: %s', playlist_content)
                return
            return list(set(
                self.__getattribute__(
                    '_parse_{}'.format(playlist_type))(playlist_content)))
        except AttributeError:
            self.logger.warning(
                'Playlist_type not supported: %s', playlist_type)
        except:
            self.logger.error(traceback.format_exc())

    def _parse_m3u(self, playlist_content):
        """Get URL(s) from M3U playlist.

        Just get non-blank lines not starting with '#'.
        """
        return [i for i in playlist_content.splitlines()
                if i.strip() and not i.startswith('#')]

    def _parse_stupid_drm(self, playlist_content):
        """Get stream URL from Stupid DRM.

        Stupid DRM returns stream URL in response body of a HTTP Request."""
        return [playlist_content.strip()]

    def _parse_pls(self, playlist_content):
        """Get URL(s) from PLS playlist.

        Just get non-blank lines not starting with '#'.
        """
        return [i.split('=', 1)[1].strip()
                for i in playlist_content.splitlines()
                if i.strip() and
                i.lower().startswith('file') and '=' in i]

    def _parse_asx(self, playlist_content):
        """Get URL(s) from ASX playlist which is an XML doc.

        The most unreliable parser due to following reasons:
        * XML tags and attributes is case-insensitive in ASX
        *   I'm turning all content into lower case
        *   since most URLs are lower cased
        * mms is not a protocol, it's a group of possible protocols, i.e.:
        *   rtsp (most common now)
        *   mmsh (which may be displayed as http)
        *   mmst (old and deprecated from now on, but still exists

        ASX Sample: http://www.orsradio.com/wma/rocktop40.asx
        """
        result = []
        xp = XMLParser('entry/ref/@href')
        tmp = xp.parse(playlist_content.lower())
        for u in tmp:
            if u.startswith('http://'):
                result.append(u.replace('http://', 'mmsh://'))
            elif u.startswith('mms://'):
                result.append(u.replace('mms://', 'rtsp://'))
                result.append(u.replace('mms://', 'mmsh://'))
                result.append(u.replace('mms://', 'mmst://'))
            else:
                result.append(u)
        return result

    def _parse_wax(self, playlist_content):
        """Variation of ASX."""
        return self._parse_asx(playlist_content)

    def _parse_wvx(self, playlist_content):
        """Variation of ASX."""
        return self._parse_asx(playlist_content)

    def _parse_wpl(self, playlist_content):
        """Get URL(s) from WPL playlist which is an XML doc."""
        xp = XMLParser('body/seq/media/@src')
        return xp.parse(playlist_content)
