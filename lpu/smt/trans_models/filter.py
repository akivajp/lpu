#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''phrase/rule table filtering function'''

# Standard libraries
import argparse
import os
import pprint
import re
import sys
import subprocess

# Local libraries
from lpu.common import files
from lpu.common import progress
from lpu.smt.trans_models import records

def matchRules(rec, rules):
    for rule in rules:
        expr = rule
        expr = re.sub('c\.c', str(rec.counts.cooc),  expr)
        expr = re.sub('c\.s', str(rec.counts.src), expr)
        expr = re.sub('c\.t', str(rec.counts.trg), expr)
        #debug.log(expr)
        if eval(expr):
            #print("MATCH")
            pass
        else:
            #print("MISMATCH")
            return False
    return True

def saveRecords(saveFile, records, nbest):
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
def filterTable(srcFile, saveFile, rules, nbest, RecordClass = records.MosesRecord):
    #if type(srcFile) == str:
    #    #srcFile = files.open(srcFile)
    #    srcFile = files.open(srcFile, 'rt')
    if type(saveFile) == str:
        saveFile = files.open(saveFile, 'wt')
    #if progress:
    #    srcFile = progress.view(srcFile)
    #srcFile = progress.view(srcFile, 'processing')
    records = []
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
def filterMosesTable(srcFile, saveFile, rules, nbest):
    #filterTable(srcFile, saveFile, rules, nbest, progress = progress, RecordClass = records.MosesRecord)
    filterTable(srcFile, saveFile, rules, nbest, RecordClass = records.MosesRecord)

#def main():
#    epilog = '''
#each rule should be as '{varname} {<,<=,==,>=,>} {value}'
#varnames:
#    c.s : source count
#    c.t : target count
#    c.c : co-occurrence count
#example:
#    %s model/phrase-table.gz model/filtered-table.gz 'c.c > 1'
#    ''' % sys.argv[0]
#    parser = argparse.ArgumentParser(
#        formatter_class=argparse.RawDescriptionHelpFormatter,
#        description='filter moses phrase-table by supplied rules',
#        epilog = epilog,
#    )
#    parser.add_argument('srcFile',  help='file path to load phrase-table')
#    parser.add_argument('saveFile', help='file path to save phrase-table')
#    parser.add_argument('rules', metavar='rule', nargs='+', help='filtering rule to save record')
#    parser.add_argument('--nbest', '-n', type=int, default=0,
#                        help='target variation limit for one source')
#    parser.add_argument('--progress', '-p', action='store_true',
#                        help='show progress bar (pv command should be installed')
#    args = vars(parser.parse_args())
#    #print(args)
#    filterMosesTable(**args)

def filterTravatarTable(srcFile, saveFile, rules, nbest, progress = False):
    #filterTable(srcFile, saveFile, rules, nbest, progress = progress, RecordClass = records.TravatarRecord)
    filterTable(srcFile, saveFile, rules, nbest, RecordClass = records.TravatarRecord)

def main():
    epilog = '''
each rule should be as '{varname} {<,<=,==,>=,>} {value}'
varnames:
    c.s : source count
    c.t : target count
    c.c : co-occurrence count
example:
    %s model/rule-table.gz model/filtered-table.gz 'c.c > 1'
    ''' % sys.argv[0]
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
    #print(args)
    filterTravatarTable(**args)

if __name__ == '__main__':
    main()

