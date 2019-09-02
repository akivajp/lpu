#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Pipe-view script for I/O progress'''

# Standard libraries
import argparse
import sys

# Local libraries
from lpu.common import logging
from lpu.common.progress import pipe_view

logger = logging.getColorLogger(__name__)

DEFAULT_REFRESH_INTERVAL = 0.5

def cmdPipeView(args):
    parser = argparse.ArgumentParser(description='Show the progress of pipe I/O')
    parser.add_argument('filepaths', metavar="filepath", nargs="*", type=str, help='path of file to load')
    parser.add_argument('--lines', '-l', action='store_true', help='line count mode (default: byte count mode)')
    parser.add_argument('--refresh', '-r', type=float, default=DEFAULT_REFRESH_INTERVAL, help='refresh interval (default: %(default)s')
    parser.add_argument('--header', '-H', type=str, help='header of the progress information')
    parsed = parser.parse_args(args)
    logger.debug(parsed)
    mode = 'bytes'
    if parsed.lines:
        mode = 'lines'
    pipe_view(parsed.filepaths, mode=mode, header=parsed.header, refresh=parsed.refresh)

def main():
    cmdPipeView(sys.argv[1:])

if __name__ == '__main__':
    main()
