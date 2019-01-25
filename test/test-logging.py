#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lpu.common import logging

import time

import traceback

if __name__ == '__main__':
    logger = logging.getColorLogger(__name__)
    formatter = logger.handlers[0].formatter
    logger.debug(logger.level, stack_info=True)
    logger.setLevel(logging.DEBUG)
    logger.debug(logger.level, stack_info=True)
    logger.debug("debug")
    logger.debug("debug", stack_info=True)
    logger.info("info")
    logger.warning("warning")
    logger.error("error")
    try:
        raise RuntimeError("runtime error")
    except Exception as e:
        logger.exception(e)
        formatter.setColor('exception', 'yellow')
        try:
            raise RuntimeError("runtime error 2")
        except Exception as e2:
            logger.exception(e2)
            logger.exception(e)
        #fmt = traceback.format_exc(e)
        #fmt = traceback.format_exc()
        logger.exception(e)
        #fmt = traceback.format_exception(Exception,e)
        #logger.debug(fmt)
        logger.debug(e)

