# co_common

Consists of the following parts:

## Audio Tools (audio)
* auconverter.py - converters, now only aac2m4a converter
* auprober.py - prober with ffmpeg and mediainfo
* wavfile.py - wave file analyzer

## Quick Config (quick_config)
* config_log.py - log parser

## System Monitor for Linux (sys_mon)
* sysinfo.py (entrance)
* sysstat.py (imported by sysinfo.py)

## Third Party SDKs (third_party_sdk)
* storage.py
*   oss (requires ali_oss_python3_sdk, check my other repos)
* weixin.py (wechat)

## Other utilities (utils)
* parser.py - parser to parse playlists, xml / html content and plaintexts
* tricks.py - many tricks, check the content
