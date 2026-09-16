#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [
    'common',
    'commands',
    'data_structs',
    'smt',
    #'__system__',
]

# initializing

import os.path
from . common import logging

version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
__version__ = open(version_file).read().strip()

logger = logging.getColorLogger(__name__)

if logging.get_quiet_status():
    logger.setLevel(logging.ERROR)
elif logging.get_debug_status():
    logger.setLevel(logging.DEBUG)
else:
    # verbose mode
    logger.setLevel(logging.INFO)

if logging.get_debug_status():
    logger.debug("Initialized LPU")
    # Report whether the C extensions (lpu.smt.* and lpu.data_structs.trie)
    # are available. The pure Python part such as lpu.common.* works without them.
    # C 拡張 (lpu.smt.* および lpu.data_structs.trie) が利用可能かを報告する。
    # これらが無くても lpu.common.* 等の純 Python 部分は動作する。
    try:
        from lpu.smt.align import ibm_models  # noqa: F401
        logger.debug("C extensions are available")
    except ImportError as _exc:
        logger.debug("C extensions are not available: %s" % (_exc,))
