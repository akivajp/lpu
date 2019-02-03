#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lpu.common import logging
from lpu.common.logging import debug_print as dprint

if __name__ == '__main__':
    logger = logging.getColorLogger(__name__)
    print(logger.handlers)
    formatter = logger.handlers[0].formatter
    logger.info("-----")
    logger.info("testing colorized logger instance")
    logger.debug(logger.level)
    #logger.setLevel(logging.DEBUG)
    config = logging.using_config(logger, debug=True)
    logger.debug(logger.level)
    logger.debug("debug")
    try:
        logger.debug("debug", stack_info=True)
    except Exception as e:
        logger.exception(repr(e))
    logger.info("info")
    logger.warning("warning")
    logger.error("error")
    logger.critical("critical")
    try:
        raise RuntimeError("runtime error")
    except Exception as e:
        logger.exception(repr(e))
        formatter.setColor('exception', 'yellow')
        try:
            raise RuntimeError("runtime error 2")
        except Exception as e2:
            logger.exception(repr(e2))
            logger.exception(repr(e))
        logger.exception(e)
        logger.debug(e)

    logger.info("-----")
    logger.info("testing debug_print function")
    def f():
        dprint("debug print", 1)
        dprint("debug print", 2)
        dprint("debug print", 3)
    f()

