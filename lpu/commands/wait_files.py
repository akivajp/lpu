#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard libraries
import argparse
import os
import sys
import time

# Local libraries
from lpu.common import logging

logger = logging.getColorLogger(__name__)

def waitFile(filepath, interval=1, timeout=0):
    if interval < 0:
        interval = 1
    if not os.path.exists(filepath):
        logger.info("Waiting for file: %s" % filepath)
        firstTime = time.time()
    while not os.path.exists(filepath):
        time.sleep(interval)
        elapsed = time.time() - firstTime
        if timeout > 0 and elapsed > timeout:
                logger.error("Waiting file (%s) was timed out (%s seconds)" % (filepath, timeout))
    logger.info("File exists: %s" % filepath)
    return True

def waitFiles(filepaths, interval=1, timeout=0):
    if type(filepaths) == str:
        filepaths = [filepaths]
    for path in filepaths:
        waitFile(path, interval, timeout)

def cmdWaitFiles(args):
    parser = argparse.ArgumentParser(description='Wait until file will be found')
    parser.add_argument('filepaths', metavar='filepath', nargs='+', help='file path for waiting')
    parser.add_argument('--quiet', '-q', action='store_true', help='quiet mode')
    parser.add_argument('--debug', '-D', action='store_true', help='debug mode')
    parser.add_argument('--interval', '-i', default=1, type=float, help='interval for next trial (default: %(default)s seconds)')
    parser.add_argument('--timeout', '-t', default=0, type=float, help='time limit in waiting file')
    parsed = parser.parse_args(args)
    with logging.using_config(logger) as c:
        if parsed.debug:
            c.set_debug(True)
            c.set_quiet(False)
        if parsed.quiet:
            c.set_quiet(True)
            c.set_debug(False)
        logger.debug(parsed)
        #waitFiles(**vars(parsed))
        waitFiles(parsed.filepaths, parsed.interval, parsed.timeout)

def main():
    cmdWaitFiles(sys.argv[1:])

if __name__ == '__main__':
    main()

