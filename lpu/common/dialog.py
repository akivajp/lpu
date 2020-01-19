#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''User-dialog functions'''

import os
import sys

def get_yes_no_string(default=None):
    if default == "yes":
        return "[Y/n]"
    elif default == "no":
        return "[y/N]"
    else:
        return "[y/n]"

def get_answer(default=None):
    ans = sys.stdin.readline().strip().lower()
    if ans in ("yes", "y"):
        return True
    elif ans in ("no", "n"):
        return False
    elif not ans:
        return default
    else:
        return None

def ask_continue(default=None):
    str_yes_or_no = get_yes_no_string(default)
    sys.stderr.write("Do you want to continue? %s: " % str_yes_or_no)
    sys.stderr.flush()
    ans = get_answer(default)
    while ans is None:
        sys.stderr.write("Do you want to continue? %s: " % str_yes_or_no)
        sys.stderr.flush()
        ans = get_answer(default)
    if not ans:
        sys.exit(1)

def ask_continue_if_exist(filepath, default=None):
    if os.path.exists(filepath):
        sys.stderr.write('"%s" is found. ' % filepath)
        return ask_continue(default)
