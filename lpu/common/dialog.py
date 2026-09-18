#!/usr/bin/env python

'''User-dialog functions'''

import os
import sys

def get_yes_no_string(default: str | None = None) -> str:
    if default == "yes":
        return "[Y/n]"
    elif default == "no":
        return "[y/N]"
    else:
        return "[y/n]"

def get_answer(default: str | None = None) -> bool | None:
    ans = sys.stdin.readline().strip().lower()
    if not ans:
        ans = default
    if ans in ("yes", "y"):
        return True
    elif ans in ("no", "n"):
        return False
    else:
        return None

def ask_continue(default: str | None = None) -> None:
    str_yes_or_no = get_yes_no_string(default)
    sys.stderr.write(f"Do you want to continue? {str_yes_or_no}: ")
    sys.stderr.flush()
    ans = get_answer(default)
    while ans is None:
        sys.stderr.write(f"Do you want to continue? {str_yes_or_no}: ")
        sys.stderr.flush()
        ans = get_answer(default)
    if not ans:
        sys.exit(1)

# ask_continue は常に None を返す (継続時はそのまま戻り、
# 拒否時は sys.exit(1) で終了する) ため、戻り値型は None で統一する
def ask_continue_if_exist(filepath: str, default: str | None = None) -> None:
    if os.path.exists(filepath):
        sys.stderr.write(f'"{filepath}" is found. ')
        ask_continue(default)
