#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [
    'common',
    'commands',
    'data_structs',
    'smt',
    '__system__',
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

logger.debug("Initialized LPU")

