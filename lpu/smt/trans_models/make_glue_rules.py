#!/usr/bin/env python

'''glue rules extracting function'''

# Standard libraries
from __future__ import annotations

import argparse
import io
from typing import cast

# Local libraries
from lpu.common import files
from lpu.common.progress import view
from lpu.smt.trans_models import records

def makeGlueRules(srcRuleTable: str | io.TextIOBase,
                  saveRules: str | io.TextIOBase,
                  progress: bool = False) -> None:
    setTags = set()
    setPOSTags = set()
    # files.open の戻り型 (IOBase) は広いため、テキストモードの結果を
    # TextIOBase に cast して狭める
    if isinstance(srcRuleTable, str):
      #srcRuleTable = files.open(srcRuleTable)
      srcRuleTable = cast(io.TextIOBase, files.open(srcRuleTable, 'rt'))
    if isinstance(saveRules, str):
        saveRules = open(saveRules, 'w', encoding='utf-8')
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
            saveRules.write(f"x0:{tag} @ S ||| x0:{tag} @ S ||| glue=1\n")
    for tag in setPOSTags:
        if tag != "X":
            saveRules.write(f"x0:X @ {tag} ||| x0:X @ {tag} ||| glue=1 unk=1\n")
    #saveRules.write("x0:X x1:X @ X ||| x0:X x1:X @ X ||| glue=1\n")
    saveRules.write("x0:X x1:X @ X ||| x0:X x1:X @ X ||| glue=1 unk=1\n")

def main() -> None:
    parser = argparse.ArgumentParser(
        description='generate glue rules from travatar rule table'
    )
    parser.add_argument('srcRuleTable',  help='file path to load rule-table')
    parser.add_argument('saveRules', help='file path to save glue rules')
    parser.add_argument('--progress', '-p', action='store_true',
                        help='show progress bar (pv command should be installed')
    args = vars(parser.parse_args())
    makeGlueRules(**args)

if __name__ == '__main__':
    main()

