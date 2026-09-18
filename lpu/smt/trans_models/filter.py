#!/usr/bin/env python

'''phrase/rule table filtering function'''

# Standard libraries
from __future__ import annotations

import argparse
import io
import re
import sys
from typing import Any
from typing import cast

# Local libraries
from lpu.common import files
from lpu.common import progress
from lpu.smt.trans_models import records

def matchRules(rec: Any, rules: list[str]) -> bool:
    for rule in rules:
        expr = rule
        expr = re.sub(r'c\.c', str(rec.counts.cooc),  expr)
        expr = re.sub(r'c\.s', str(rec.counts.src), expr)
        expr = re.sub(r'c\.t', str(rec.counts.trg), expr)
        #debug.log(expr)
        if eval(expr):
            pass
        else:
            return False
    return True

# 呼び出し元 (filterTable) がパスをファイルオブジェクトへ変換済みのため、
# ファイルオブジェクトのみを受け付ける
def saveRecords(saveFile: io.TextIOBase, records: list[Any], nbest: int) -> None:
    pairs = []
    if nbest > 0:
        for i, rec in enumerate(records):
            pairs.append( (rec.features['egfp'],i) )
        pairs.sort(reverse = True)
        newRecords = []
        for _, i in pairs[:nbest]:
            newRecords.append( records[i] )
        records = newRecords
    for rec in records:
        saveFile.write(rec.to_str())
        saveFile.write("\n")

#def filterTable(srcFile, saveFile, rules, nbest, progress = False, RecordClass = records.MosesRecord):
def filterTable(
    srcFile: str | io.TextIOBase,
    saveFile: str | io.TextIOBase,
    rules: list[str],
    nbest: int,
    RecordClass: Any = records.MosesRecord,
) -> None:
    #if type(srcFile) == str:
    #    #srcFile = files.open(srcFile)
    #    srcFile = files.open(srcFile, 'rt')
    # files.open の戻り型 (IOBase) は広いため、テキストモードの結果を
    # TextIOBase に cast して狭める
    if isinstance(saveFile, str):
        saveFile = cast(io.TextIOBase, files.open(saveFile, 'wt'))
    #if progress:
    #    srcFile = progress.view(srcFile)
    #srcFile = progress.view(srcFile, 'processing')
    records: list[Any] = []
    lastSrc = ''
    for line in progress.view(srcFile, 'processing'):
        rec = RecordClass(line)
        if rec.src != lastSrc:
            lastSrc = rec.src
            if records:
                saveRecords(saveFile, records, nbest)
                records = []
        if matchRules(rec, rules):
            records.append( rec )
#          output.write( rec.to_str() )
    if records:
        saveRecords(saveFile, records, nbest)
    saveFile.close()

#def filterMosesTable(srcFile, saveFile, rules, nbest, progress = False):
def filterMosesTable(srcFile: str | io.TextIOBase, saveFile: str | io.TextIOBase,
                     rules: list[str], nbest: int) -> None:
    #filterTable(srcFile, saveFile, rules, nbest, progress = progress, RecordClass = records.MosesRecord)
    filterTable(srcFile, saveFile, rules, nbest, RecordClass = records.MosesRecord)

#    %s model/phrase-table.gz model/filtered-table.gz 'c.c > 1'
#        description='filter moses phrase-table by supplied rules',
#    parser.add_argument('srcFile',  help='file path to load phrase-table')
#    parser.add_argument('saveFile', help='file path to save phrase-table')
#    filterMosesTable(**args)

def filterTravatarTable(srcFile: str | io.TextIOBase, saveFile: str | io.TextIOBase,
                        rules: list[str], nbest: int, progress: bool = False) -> None:
    #filterTable(srcFile, saveFile, rules, nbest, progress = progress, RecordClass = records.TravatarRecord)
    filterTable(srcFile, saveFile, rules, nbest, RecordClass = records.TravatarRecord)

def main() -> None:
    epilog = f'''
each rule should be as '{{varname}} {{<,<=,==,>=,>}} {{value}}'
varnames:
    c.s : source count
    c.t : target count
    c.c : co-occurrence count
example:
    {sys.argv[0]} model/rule-table.gz model/filtered-table.gz 'c.c > 1'
    '''
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='filter travatar rule-table by supplied rules',
        epilog = epilog,
    )
    parser.add_argument('srcFile',  help='file path to load rule-table')
    parser.add_argument('saveFile', help='file path to save rule-table')
    parser.add_argument('rules', metavar='rule', nargs='+', help='filtering rule to save record')
    parser.add_argument('--nbest', '-n', type=int, default=0,
                        help='target variation limit for one source')
    parser.add_argument('--progress', '-p', action='store_true',
                        help='show progress bar (pv command should be installed')
    args = vars(parser.parse_args())
    filterTravatarTable(**args)

if __name__ == '__main__':
    main()

