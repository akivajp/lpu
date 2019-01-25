#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''functions to normalize phrase translation probabilities of given phrase/rule table'''

# Standarde libraries
import argparse
import math
import sys

# Local libraries
from lpu.common import files
from lpu.common import logging
from lpu.common import progress
from lpu.smt.trans_models.records import MosesRecord, TravatarRecord
from lpu.smt.trans_models.tables import Table

#from lpu.data_structs import trees

def get_target_field(rec, target_number=None):
    if isinstance(target_number,int):
        return rec.trg.split('|COL|')[target_number].strip()
    else:
        return rec.trg

def calc_src_factor(table, src, target_number=None):
    total = 0
    feature = 'egfp'
    targets = set()
    if target_number:
        feature = str(target_number) + feature
    for i, rec in enumerate( table.find_src(src) ):
        target = get_target_field(rec,target_number)
        if target not in targets:
            total += rec.features[feature]
            targets.add(target)
    return total

def calc_trg_factor(table, trg, target_number=None):
    total = 0
    feature = 'fgep'
    if target_number:
        feature = str(target_number) + feature
    sources = set()
    #for i, rec in enumerate( table.find_trg(trg) ):
    #for i, rec in enumerate( table.find(trg) ):
    for i, rec in enumerate( table.find_trg(trg, target_number) ):
        #logging.log((i, rec.to_str()))
        #if target_number == 0:
        #    logging.log(trg)
        #    logging.log(get_target_field(rec,target_number))
        #    logging.log(rec.to_str())
        #    logging.log(feature)
        #    logging.log(rec.features[feature])
        #    logging.log("--")
        #if trg == get_target_field(rec,target_number):
        if rec.src not in sources:
            total += rec.features[feature]
            sources.add(rec.src)
    return total

def normalize_table(table_path, save_path):
    table = Table(table_path, TravatarRecord, trg_key=True)

    last_src = ""
    #src_total = 0
    src_total = {}
    dict_trg_total = {}
    with files.open(save_path, 'wt') as fobj_out:
        #for i, rec in enumerate( progress.view(table, 'normalizing', max_count = len(table)) ):
        for i, line in enumerate( progress.view(table_path, 'normalizing', max_count = len(table)) ):
            try:
                rec = table.RecordClass(line)
                #if i > 100:
                #    break
                targets = [rec.trg]
                target_numbers = [None]
                if rec.trg.find('|COL|') >= 0:
                    for i, field in enumerate(rec.trg.split('|COL|')):
                        targets.append(field.strip())
                        target_numbers.append(i)
                old = rec.to_str()
                if last_src != rec.src:
                    for num in target_numbers:
                        src_total[num] = calc_src_factor(table, rec.src, num)
                    last_src = rec.src
                for num, target in zip(target_numbers, targets):
                    #logging.log(target)
                    trg_track = table.field_dict.get_node(target).track()
                    if (num,trg_track) in dict_trg_total:
                        trg_total = dict_trg_total[num,trg_track]
                    else:
                        #trg_total = calc_trg_factor(table, rec.trg, num)
                        trg_total = calc_trg_factor(table, target, num)
                        dict_trg_total[num, trg_track] = trg_total
                    prefix = ''
                    if isinstance(num,int):
                        prefix=str(num)
                    rec.features[prefix+'egfp'] /= src_total[num]
                    rec.features[prefix+'fgep'] /= trg_total
                #if old != rec.to_str():
                #    logging.log("old: %s" % old)
                #    logging.log("new: %s" % rec.to_str())
                #    logging.log("--")
                fobj_out.write(rec.to_str())
                fobj_out.write("\n")
            except Exception as e:
                logging.warn("source: %s" % rec.src)
                logging.warn("target: %s" % rec.trg)
                logging.warn("num: %s" % num)
                logging.warn("target: %s" % target)
                logging.warn(e)
                raise Exception()

def main():
    parser = argparse.ArgumentParser(description = 'load 2 rule tables and pivot into one travatar rule table')
    parser.add_argument('table_path', type=str, help = 'path to phrase/rule table')
    parser.add_argument('save_path', help = 'path to save phrase/rule table')
    args = parser.parse_args()

    normalize_table(args.table_path, args.save_path)

if __name__ == '__main__':
    main()

