#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard libraries
import argparse
import sys

# Local libraries
from lpu.common import logging
from lpu.common.files import wait_files

logger = logging.getColorLogger(__name__)

def cmd_wait_files(args):
    parser = argparse.ArgumentParser(description='wait until file will be found')
    parser.add_argument('filepaths', metavar='filepath', nargs='+', help='file path for waiting')
    parser.add_argument('--quiet', '-q', action='store_true', help='quiet mode')
    parser.add_argument('--debug', '-D', action='store_true', help='debug mode')
    parser.add_argument('--delay', '-d', default=0, type=float, help='duration to waiting time before the first check (default: %(default)s)')
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
        wait_files(parsed.filepaths, parsed.interval, parsed.timeout, parsed.quiet)

def main():
    cmd_wait_files(sys.argv[1:])

if __name__ == '__main__':
    main()

