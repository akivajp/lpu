#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = [
    'backends',
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
    from . backends import safe_cython
    if safe_cython.available:
        logger.debug("Cython is available")
        if safe_cython.compiled:
            logger.debug("Running with compiled LPU")
        else:
            logger.debug("Running with not compiled LPU")
    else:
        logger.debug("Cython is not available")
