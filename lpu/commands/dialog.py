#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

from lpu.common.dialog import ask_continue
from lpu.common.dialog import ask_continue_if_exist

def cmd_dialog(args):
    parser = argparse.ArgumentParser(description="Show message on condition, wait and receive user's response")
    parser.add_argument('--exist', '-e', metavar='filepath', type=str, help='asking whether continuing when specified file already exists')
    parser.add_argument('--continue', '-c', action='store_true', help='asking whether continuing')
    parser.add_argument('--yes', '-y', action='store_true', help='assign the default answer as "Yes"')
    parser.add_argument('--no', '-n', action='store_true', help='assign the default answer as "No"')
    parsed = parser.parse_args(args)
    default = None
    if parsed.yes:
        default = 'yes'
    if parsed.no:
        default = 'no'
    if getattr(parsed, 'continue'):
        return ask_continue(default)
    elif parsed.exist:
        return ask_continue_if_exist(parsed.exist, default)
    else:
        sys.exit(1)

def main():
    cmd_dialog(sys.argv[1:])

if __name__ == '__main__':
    main()
