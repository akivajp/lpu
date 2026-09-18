#!/usr/bin/env python

'''function converting rule table'''

# Standard libraries
from __future__ import annotations

import argparse
import io
from typing import cast

# Local libraries
from lpu.common import files
from lpu.common.progress import view
from lpu.smt.trans_models import records

CONVERT_OPTIONS=["scfg", "hiero", "tag"]

def convertTravatarExtract(
    srcFile: str | io.TextIOBase,
    saveFile: str | io.TextIOBase,
    sync: str | None = None,
    flatten: str | None = None,
    reverse: bool = False,
    no_unary: bool = False,
    progress: bool = False,
) -> None:
    # files.open は gzip 透過のため typeshed 上の戻り型が広い (IOBase)。
    # テキストモードでの結果は TextIOBase なので cast で狭める
    if isinstance(srcFile, str):
        #srcFile = files.open(srcFile)
        srcFile = cast(io.TextIOBase, files.open(srcFile, 'rt'))
    if isinstance(saveFile, str):
        saveFile = cast(io.TextIOBase, files.open(saveFile, 'wt'))
    if progress:
        srcFile = view(srcFile)
    for line in srcFile:
        fields = line.strip().split('|||')
        fields = [f.strip() for f in fields]
        if len(fields) >= 4:
            srcSymbols = fields[0].strip().split(' ')
            trgSymbols = fields[1].strip().split(' ')
            if sync:
                srcSymbols, trgSymbols = records.syncTags(srcSymbols, trgSymbols, sync)
                trgSymbols, srcSymbols = records.syncTags(trgSymbols, srcSymbols, sync)
            if flatten:
                srcSymbols = records.getFlattenSymbols(srcSymbols, flatten)
                trgSymbols = records.getFlattenSymbols(trgSymbols, flatten)
            if reverse:
                srcSymbols, trgSymbols = trgSymbols, srcSymbols
                aligns = records.getAlignSet(fields[3])
                aligns = records.getRevAlignSet(aligns)
                fields[3] = str.join(' ', sorted(aligns))
            if no_unary:
                #if len(records.getTravatarTerms(srcSymbols)) == 0:
                if len(records.TravatarRecord.getTerms(srcSymbols)) == 0:
                    # no terminals
                    continue
#                if len(srcSymbols) == 3:
#                    tag = srcSymbols[2]
#                    if srcSymbols[0] == "x0:"+tag:
#                        # src is unary cycle
            fields[0] = str.join(' ', srcSymbols)
            fields[1] = str.join(' ', trgSymbols)
            fields[0], fields[1] = records.TravatarRecord.fixOrderStrings(fields[0], fields[1])
            saveFile.write(str.join(' ||| ', fields)+"\n")
    saveFile.close()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('src_table', help = 'source rule table')
    parser.add_argument('save_table', help = 'save path')
    parser.add_argument('--sync', choices=CONVERT_OPTIONS, help='transfer the phrase tags from subtrees')
    parser.add_argument('--flatten', choices=CONVERT_OPTIONS, help='flatten the trees into symbols string in specified style')
    parser.add_argument('--reverse', action='store_true', help='reverse the trasnlation direction of records')
    parser.add_argument('--no-unary', dest='no_unary', action='store_true', help='avoid unary cycle')
    parser.add_argument('--progress', '-p', action='store_true', help='show progress')
    args = parser.parse_args()
    #args = vars(parser.parse_args())
    convertTravatarExtract(args.src_table, args.save_table, args.sync, args.flatten, args.reverse, args.no_unary, args.progress)

if __name__ == '__main__':
    main()

