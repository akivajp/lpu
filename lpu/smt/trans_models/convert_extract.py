#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''function converting rule table'''

# Standard libraries
import argparse
import subprocess

# Local libraries
from lpu.common import files
from lpu.common.progress import view
from lpu.smt.trans_models import records

CONVERT_OPTIONS=["scfg", "hiero", "tag"]

def convertTravatarExtract(srcFile, saveFile, sync=None, flatten=None, reverse=False, no_unary=False, progress=False):
    if type(srcFile) == str:
        #srcFile = files.open(srcFile)
        srcFile = files.open(srcFile, 'rt')
    if type(saveFile) == str:
        saveFile = files.open(saveFile, 'wt')
    if progress:
        srcFile = view(srcFile)
    for line in srcFile:
        fields = line.strip().split('|||')
        fields = [f.strip() for f in fields]
        if len(fields) >= 4:
            srcSymbols = fields[0].strip().split(' ')
            trgSymbols = fields[1].strip().split(' ')
            count = fields[2].strip()
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
#                        continue
            fields[0] = str.join(' ', srcSymbols)
            fields[1] = str.join(' ', trgSymbols)
            fields[0], fields[1] = records.TravatarRecord.fixOrderStrings(fields[0], fields[1])
            saveFile.write(str.join(' ||| ', fields)+"\n")
    saveFile.close()

def main():
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
    #print(args)
    convertTravatarExtract(args.src_table, args.save_table, args.sync, args.flatten, args.reverse, args.no_unary, args.progress)

if __name__ == '__main__':
    main()

