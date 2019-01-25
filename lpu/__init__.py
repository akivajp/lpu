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

from . common import logging

logger = logging.getColorLogger(__name__)

if logging.get_quiet_status():
    logger.setLevel(logging.ERROR)
elif logging.get_debug_status():
    logger.setLevel(logging.DEBUG)
else:
    # verbose mode
    logger.setLevel(logging.INFO)

logger.debug("Initialized LPU")

