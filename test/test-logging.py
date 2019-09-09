#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  test the module: lpu.common.logging
"""

from lpu.common import logging
#from lpu.common.logging import debug_print as dprint
logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

if __name__ == '__main__':
    logger.info(logging)
    logger.info(logger.handlers)
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
        #dprint(100)
        #dprint(200, 2)
        #dprint( (100, 200 * 2, "abc" * 2, ), 2)
        #dprint((100, 200 * 2, "abc" * 2))
        #dprint(
        #    (100,
        #     200 * 2,
        #     "abc" * 2),
        #     3,
        #     offset=0,
        #)
        #dprint( (100, ")" ) )
        #dprint( (100, ",,,200" ) )
        #dprint( ",,,)))" )
        #dprint( "))),,," )
    f()
    #def g():
    #    f()
    #g2 = g
    #g()
    #g2()
