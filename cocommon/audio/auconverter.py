#!/usr/bin/env python3

import os
import logging

from ..utils import tricks
from . import auprober


def convert_adts_to_m4a(fn, remove_original=True):
    """Use MP4Box to convert aac file in adts to m4a file.

    Note MP4Box will automatically add faststart movflags
    If file have SBR with it (HE-AAC), add '-sbr' output option
    Further if file have PS with it (HE-AACv2), add '-ps' output option

    :param remove_original: remove original aac file if convert succeeds
    """
    logger = logging.getLogger(__name__)
    if fn.endswith('.aac'):
        output_fn = fn[:-4] + '.m4a'
    else:
        output_fn = fn + '.m4a'
    if os.path.isfile(output_fn):
        os.remove(output_fn)

    aac_prober = auprober.AudioProber(fn)
    aac_profile = aac_prober.get_aac_profile()
    if aac_profile is None:
        return None
    if aac_profile == 'non-aac':
        return fn
    if aac_profile == 'aac_he_v2':
        flags = ['-sbr', '-ps']
    elif aac_profile == 'aac_he':
        flags = ['-sbr']
    else:
        flags = []
    cmd = ['MP4Box', '-add', fn] + flags + [output_fn]
    try:
        tricks.retry(3, tricks.run_cmd_to_generate_files, cmd, [output_fn])
        if remove_original:
            os.remove(fn)
        return output_fn
    except Exception as e:
        logger.warn(e)
        return None
