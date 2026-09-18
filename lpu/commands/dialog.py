#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

from lpu.common.dialog import ask_continue
from lpu.common.dialog import ask_continue_if_exist

def cmd_dialog(args: list[str]) -> None:
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
    # 中断時は ask_continue 側で sys.exit(1) するため、
    # 戻り値を受け取って返す必要は無い
    if getattr(parsed, 'continue'):
        ask_continue(default)
    elif parsed.exist:
        ask_continue_if_exist(parsed.exist, default)
    else:
        sys.exit(1)

def main() -> None:
    cmd_dialog(sys.argv[1:])

if __name__ == '__main__':
    main()
