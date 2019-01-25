#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys

def defaultString(default):
    if default == "yes":
        return "[Y/n]"
    elif default == "no":
        return "[y/N]"
    else:
        return "[y/n]"

def getAnswer(default):
    ans = sys.stdin.readline().strip().lower()
    if ans in ("yes", "y"):
        return True
    elif ans in ("no", "n"):
        return False
    elif len(ans) == 0:
        return default
    else:
        return None

def askContinue(default=None):
    strYN = defaultString(default)
    sys.stderr.write("Do you want to continue? %s: " % strYN)
    sys.stderr.flush()
    ans = getAnswer(default)
    while ans == None:
        sys.stderr.write("Do you want to continue? %s: " % strYN)
        sys.stderr.flush()
        ans = getAnswer(default)
    if ans == False:
        sys.exit(1)

def askExistContinue(filepath, default=None):
    if os.path.exists(filepath):
        sys.stderr.write('"%s" is found. ' % filepath)
        askContinue(default)

def cmdPrompt(args):
    parser = argparse.ArgumentParser(description='Get absolute paths of given files or directories')
    parser.add_argument('--exist', '-e', type=str, help='asking whether continuing when specified file already exists')
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
        return askContinue(default)
    elif parsed.exist:
        return askExistContinue(parsed.exist, default)
    else:
        sys.exit(1)

def main():
    cmdPrompt(sys.argv[1:])

if __name__ == '__main__':
    main()

