# co_common

Consists of the following parts:

## Quick Config (quick_config)
* config_log.py - log parser
* daemonize.py - unix daemon maker

## System Monitor for Linux (sys_mon)
* sysinfo.py (entrance)
* sysstat.py (imported by sysinfo.py)

## Third Party SDKs (third_party_sdk)
* storage.py
*   oss (requires ali_oss_python3_sdk, check my other repos)
* weixin.py (wechat)

## Other utilities (utils)
* compat.py - python 2 / 3 compatible imports
* parser.py - parser to parse playlists, xml / html content and plaintexts
* tricks.py - many tricks, check the content
* rst_gen.py - restructuredText generator
