#!/usr/bin/env python

import argparse
import os
import sys

def printAbsPathList(filepaths: list[str]) -> None:
    print(str.join(' ', map(os.path.abspath, filepaths)))

def cmdAbsPath(args: list[str]) -> None:
    parser = argparse.ArgumentParser(description='Get absolute paths of given files or directories')
    parser.add_argument('filepaths', metavar="filepath", nargs="+", type=str, help='path of file to get the absolute paths')
    parsed = parser.parse_args(args)
    printAbsPathList(parsed.filepaths)

def main() -> None:
    cmdAbsPath(sys.argv[1:])

if __name__ == '__main__':
    main()

