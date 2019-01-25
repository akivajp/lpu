#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''glue rules extracting function'''

# Standard libraries
import argparse
import sys
import subprocess

# Local libraries
from lpu.common import files
from lpu.common.progress import view
from lpu.smt.trans_models import records

def makeGlueRules(srcRuleTable, saveRules, progress = False):
    setTags = set()
    setPOSTags = set()
    if type(srcRuleTable) == str:
      #srcRuleTable = files.open(srcRuleTable)
      srcRuleTable = files.open(srcRuleTable, 'rt')
    if type(saveRules) == str:
        saveRules = open(saveRules, 'wt')
    if progress:
        srcRuleTable = view(srcRuleTable)
    for line in srcRuleTable:
        rec = records.TravatarRecord(line)
        symbols = rec.src.split(' ')
        if len(symbols) == 3:
            if symbols[0][0] == '"' and symbols[1] == "@":
                # single source word rule
                tag = symbols[2]
                setPOSTags.add(tag)
        elif len(symbols) >= 3 and symbols[-2] == "@":
            tag = symbols[-1]
            setTags.add(tag)

    setTags.add('X')
    for tag in setTags:
        if tag != "S":
            saveRules.write("x0:%s @ S ||| x0:%s @ S ||| glue=1\n" % (tag, tag))
    for tag in setPOSTags:
        if tag != "X":
            saveRules.write("x0:X @ %s ||| x0:X @ %s ||| glue=1 unk=1\n" % (tag, tag))
    #saveRules.write("x0:X x1:X @ X ||| x0:X x1:X @ X ||| glue=1\n")
    saveRules.write("x0:X x1:X @ X ||| x0:X x1:X @ X ||| glue=1 unk=1\n")

def main():
    parser = argparse.ArgumentParser(
        description='generate glue rules from travatar rule table'
    )
    parser.add_argument('srcRuleTable',  help='file path to load rule-table')
    parser.add_argument('saveRules', help='file path to save glue rules')
    parser.add_argument('--progress', '-p', action='store_true',
                        help='show progress bar (pv command should be installed')
    args = vars(parser.parse_args())
    #print(args)
    makeGlueRules(**args)

if __name__ == '__main__':
    main()

