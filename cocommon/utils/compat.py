import sys

PY3 = sys.version_info.major == 3


if PY3:
    unicode = str
    import urllib.parse as urlparse
    import subprocess
else:
    import urlparse
    import urllib
    urlparse.quote = urllib.quote
    urlparse.quote_plus = urllib.quote_plus
    import subprocess32 as subprocess
    unicode = unicode


def get_urlparsable_string(s):
    if PY3:
        if isinstance(s, bytes):
            try:
                s = s.decode('utf-8')
            except UnicodeDecodeError:
                s = s.decode('gbk')
            except:
                pass
        if not isinstance(s, str):
            return
    else:
        if isinstance(s, unicode):
            try:
                s = s.encode('utf-8')
            except:
                pass
        if not isinstance(s, str):
            return
    return s


__all__ = [
    'urlparse',
    'get_urlparsable_string',
    'subprocess',
    'unicode',
    'PY3']
