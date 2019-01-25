#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''functions to triangulate 2 phrase tables into 1 table
by combining source-pivot and pivot-target for common pivot phrase'''

# Standarde libraries
import argparse
import math
import sys

# Local libraries
from lpu.common import compat
from lpu.common import files
from lpu.common import logging
from lpu.common import progress
from lpu.smt.trans_models.records import MosesRecord, TravatarRecord
from lpu.smt.trans_models.tables import Table

from lpu.data_structs import trees

# lower threshold of trans probs to abort
#THRESHOLD = 1e-3
THRESHOLD = 0 # not aborting

# lower guarantee for lexical trans probs
MINPROB = 10 ** -10

# limit number of records for the same source phrase
NBEST = 20

# methods to estimate trans probs (countmin/prodprob/bidirmin/bidirgmean/bidirmax/bidiravr)
method_list = ['countmin', 'prodprob', 'bidirmin', 'bidirgmean', 'bidirmax', 'bidiravr']
#METHOD = 'counts'
#METHOD = 'hybrid'
#METHOD = 'countmin'
METHOD = 'prodprob'

# methods to estimate lexical weight
lex_method_list = ['prodweight', 'countmin', 'prodprob', 'bidirmin', 'bidirgmean', 'bidirmax', 'bidiravr', 'table', 'countmin+table', 'prodprob+table', 'bidirmin+table', 'bidirgmean+table']
LEX_METHOD = 'prodweight'

# methods to estimate joint trans probs
joint_method_list = ['memoryless', 'independent']
JOINT_METHOD = 'memoryless'

# matching methods
match_method_list = ['hiero', 'symbols', 'treecomp', 'treedist', 'treedistexp']
MATCH_METHOD = 'symbols'

NULLS = 10**4

NOPREFILTER = False

class WorkSet:
    '''data set for multi-processing'''
    def __init__(self, savefile, workdir, method, **options):
        prefix = options.get('prefix', 'phrase')
        self.multi_target = options.get('multi_target', False)
        self.Record = options.get('RecordClass', MosesRecord)
        self.method = method
        self.matchMethod = options.get('matchMethod', MATCH_METHOD)
        self.jointMethod = options.get('jointMethod', JOINT_METHOD)
#        if method.find('multi') >= 0:
#            self.multi_target = True
#            self.method = method.replace('multi','').replace('+','')
        self.nbest = NBEST
        self.savePath = savefile
        self.threshold = THRESHOLD
        self.workdir = workdir
        self.foutPivot = files.open(savefile, 'wt')
        #self.pivotProc = multiprocessing.Process( target = pivotRecPairs, args = (self,) )
        #self.recordProc = multiprocessing.Process( target = writeRecordQueue, args = (self,) )
        self.numRecSrcPvt = 0
        self.setPhrasesSrcPvt = set()
        self.setWordsSrcPvt = set()
        self.numRecPvtTrg = 0
        self.setPhrasesPvtTrg = set()
        self.setWordsPvtTrg = set()
        self.numRecSrcTrg = 0
        self.setPhrasesSrcTrg = set()
        self.setWordsSrcTrg = set()

    def __del__(self):
        self.close()

    def close(self):
        if self.foutPivot:
            self.foutPivot.close()
            self.foutPivot = None
#        if self.pivotProc.pid:
#            if self.pivotProc.exitcode == None:
#                self.pivotProc.terminate()
#            self.pivotProc.join()
#        if self.recordProc.pid:
#            if self.recordProc.exitcode == None:
#                self.recordProc.terminate()
#            self.recordProc.join()
#        self.pivotQueue.close()
#        self.outQueue.close()

#    def join(self):
#        self.pivotProc.join()
#        self.recordProc.join()
#
#    def start(self):
#        self.pivotProc.start()
#        self.recordProc.start()

#    def terminate(self):
#        self.pivotProc.terminate()
#        self.recordProc.terminate()


#def updateFeatures(recPivot, recPair, method, multi_target = False, jointMethod = 'memoryless'):
def updateFeatures(recPivot, recPair, workset, multi_target = False):
    '''update features'''
    features = recPivot.features
    srcFeatures = recPair[0].features
    trgFeatures = recPair[1].features
    #logging.debug(method)
    #logging.debug(srcFeatures)
    #logging.debug(trgFeatures)
    #if method.find('prodprob') >= 0:
    if workset.method.find('prodprob') >= 0:
        # multiplying scores and marginalizing
        if not multi_target:
            for key in ['egfl', 'egfp', 'fgel', 'fgep']:
                features.setdefault(key, 0)
                if workset.matchMethod == 'hiero':
                    features[key] += (srcFeatures[key] * trgFeatures[key])
                elif workset.matchMethod == 'symbols':
                    features[key] += (srcFeatures[key] * trgFeatures[key])
                elif workset.matchMethod == 'treecomp':
                    features[key] += (srcFeatures[key] * trgFeatures[key])
                elif workset.matchMethod == 'treedist':
                    elems1 = recPair[0].trg.split(' ')[0:-1]
                    elems2 = recPair[1].src.split(' ')[0:-1]
                    tree1 = trees.parseSExpression('(' + str.join(' ', elems1) + ')')[0]
                    tree2 = trees.parseSExpression('(' + str.join(' ', elems2) + ')')[0]
                    dist = trees.calcTreeEditDistance(tree1, tree2)
                    numTerms = len(recPair[0].trgTerms)
                    numElems = max(trees.countElements(tree1), trees.countElements(tree2))
                    rate = max(1, 1 + numElems - numTerms - dist) / float(max(1, 1 + numElems - numTerms))
                    features[key] += (rate * srcFeatures[key] * trgFeatures[key])
                elif workset.matchMethod == 'treedistexp':
                    elems1 = recPair[0].trg.split(' ')[0:-1]
                    elems2 = recPair[1].src.split(' ')[0:-1]
                    tree1 = trees.parseSExpression('(' + str.join(' ', elems1) + ')')[0]
                    tree2 = trees.parseSExpression('(' + str.join(' ', elems2) + ')')[0]
                    dist = trees.calcTreeEditDistance(tree1, tree2)
                    rate = math.exp(-dist)
                    features[key] += (rate * srcFeatures[key] * trgFeatures[key])
                else:
                    assert False, 'Invalid Match Method'
        if multi_target:
            # p(trg,pvt|src) ~ p(trg|pvt) * p(pvt|src)
            features['egfp'] =  srcFeatures['egfp'] * trgFeatures['egfp']
            if workset.jointMethod == 'memoryless':
                # p(src|pvt,trg) ~ f(src|pvt)
                features['fgep'] = srcFeatures['fgep']
            else:
                features['fgep'] = 1.0
#            for key in ['egfp', 'fgep']:
#                features.setdefault(key, 0)
#                features[key] += (srcFeatures[key] * trgFeatures[key])
#            # P(trg,pvt|src) = P(trg|pvt,src) * P(pvt|src) ~ P(trg|pvt) * P(pvt|src)
#            features['egfp'] = (srcFeatures['egfp'] * trgFeatures['egfp'])
#            # P(src|pvt,trg) ~ P(src|pvt)
#            features['fgep'] = srcFeatures['fgep']
            for key in ['egfl', 'egfp', 'fgel', 'fgep']:
                features['1'+key] = srcFeatures[key]
    else:
        # multiplying only lexical weights and marginalizing
        for key in ['egfl', 'fgel']:
            features.setdefault(key, 0)
            features[key] += (srcFeatures[key] * trgFeatures[key])
    # using 'p' and 'w' of target
    if 'p' in trgFeatures:
        features['p'] = trgFeatures['p']
    if multi_target:
        if 'w' in trgFeatures:
            features['0w'] = trgFeatures['w']
        if 'w' in srcFeatures:
            features['1w'] = srcFeatures['w']
    else:
        if 'w' in trgFeatures:
            features['w'] = trgFeatures['w']


def updateCounts(recPivot, recPair, method):
    '''update occurrence counts of phrase'''
    counts = recPivot.counts
    features = recPivot.features
    if method == 'countmin':
        #counts.co = max(counts.co, min(recPair[0].counts.co, recPair[1].counts.co))
        #c = recPair[0].counts.co * recPair[1].counts.co
        c = min(recPair[0].counts.cooc, recPair[1].counts.cooc)
        counts.cooc += c
        #counts.co = counts.co + c + 2 * math.sqrt(counts.co * c)
    elif method == 'bidirmin':
        counts1 = recPair[0].counts
        counts2 = recPair[1].counts
        cooc1 = counts1.cooc * counts2.cooc / float(counts2.src)
        cooc2 = counts2.cooc * counts1.cooc / float(counts1.trg)
        counts.cooc += min(cooc1, cooc2)
#        if True:
#        if recPair[0].src.find('Dieu') >= 0:
#            progress.log("%s ||| %s ||| %s ||| (%s %s %s) * (%s %s %s) -> %s %s -> %s\n" % (recPair[0].src, recPair[0].trg, recPair[1].trg, counts1.co, counts1.src, counts1.trg, counts2.co, counts2.src, counts2.trg, co1, co2, min(co1,co2)))
    elif method == 'bidirgmean':
        counts1 = recPair[0].counts
        counts2 = recPair[1].counts
        co1 = counts1.co * counts2.co / float(counts2.src)
        co2 = counts2.co * counts1.co / float(counts1.trg)
        counts.co += math.sqrt(co1*co2)
#        progress.log("%s ||| %s ||| %s ||| (%s %s %s) * (%s %s %s) -> %s %s -> %s\n" % (recPair[0].src, recPair[0].trg, recPair[1].trg, counts1.co, counts1.src, counts1.trg, counts2.co, counts2.src, counts2.trg, co1, co2, math.sqrt(co1*co2)))
    elif method == 'bidirmax':
        counts1 = recPair[0].counts
        counts2 = recPair[1].counts
        co1 = counts1.co * counts2.co / float(counts2.src)
        co2 = counts2.co * counts1.co / float(counts1.trg)
        counts.co += max(co1, co2)
    elif method == 'bidiravr':
        counts1 = recPair[0].counts
        counts2 = recPair[1].counts
        co1 = counts1.cooc * counts2.co / float(counts2.src)
        co2 = counts2.cooc * counts1.co / float(counts1.trg)
        counts.co += (co1 + co2) * 0.5
    elif method == 'prodprob':
        counts.src  = recPair[0].counts.src
        counts.cooc = counts.src * features['egfp']
        counts.trg  = counts.cooc / features['fgep']
    elif method == 'multi':
        c = min(recPair[0].counts.co, recPair[1].counts.co)
        counts.co += c
    else:
        assert False, "Invalid method: %s" % method


def mergeAligns(recPivot, recPair):
    '''merge word alignments'''
#    if recPivot.aligns:
#      return
#    alignSet = set()
    alignMapSrcPvt = recPair[0].alignMap
    alignMapPvtTrg = recPair[1].alignMap
    for srcIndex, pvtIndices in alignMapSrcPvt.items():
        for pvtIndex in pvtIndices:
            for trgIndex in alignMapPvtTrg.get(pvtIndex, []):
              align = '%d-%d' % (srcIndex, trgIndex)
#              alignSet.add(align)
              recPivot.aligns.add(align)
#    recPivot.aligns = sorted(alignSet)


def filterByCountRatioToMax(records, div = 100):
    coMax = 0
    for rec in flattenRecords(records):
        coMax = max(coMax, rec.counts.co)
    if isinstance(records, list):
        newRecords = []
        for rec in records:
            if rec.counts.co >= coMax / float(div):
                newRecords.append( rec )
        records = newRecords
    elif isinstance(records, dict):
        newRecords = {}
        for key, rec in records.items():
            if rec.counts.co >= coMax / float(div):
                newRecords[key] = rec
        records = newRecords
    return records


def calcPhraseTransProbsByCounts(records):
    '''calculate forward phrase trans probs by occurrence counts of the phrases'''
    srcCount = calcSrcCount(records)
    for rec in records.values():
    #for rec in flattenRecords(records):
        counts = rec.counts
        counts.src = srcCount
        if srcCount > 0:
            rec.features['egfp'] = counts.co / float(srcCount)
        else:
            rec.features['egfp'] == 0


def calcPhraseTransProbsOnTable(table_path, savePath, **options):
    '''calculate phrase trans probs on the table in which co-occurrence counts are estimated'''
    method = options.get('method', METHOD)
    RecordClass = options.get('RecordClass', MosesRecord)

    table_file = files.open(table_path, "r")
    saveFile  = files.open(savePath, "w")
    records = {}
    lastSrc = ''
    for line in table_file:
        rec = RecordClass(line)
        key = "%s ||| %s |||" % (rec.src, rec.trg)
        if rec.src != lastSrc and records:
            calcPhraseTransProbsByCounts(records)
            writeRecords(saveFile, records)
            records = {}
        if rec.counts.co > 0:
            records[key] = rec
        lastSrc = rec.src
    if records:
        calcPhraseTransProbsByCounts(records)
        writeRecords(saveFile, records)
    saveFile.close()
    table_file.close()


def calcSrcCount(records):
    '''calculate source phrase occurrence counts by co-occurrence counts'''
    total = 0
    for rec in flattenRecords(records):
        total += rec.counts.co
    return total

def updateWordPairCounts(lexCounts, records):
    '''find word pairs in phrase pairs, and update the counts of word pairs'''
    if len(records) > 0:
        src_symbols = records.values()[0].src_symbols
        if len(src_symbols) == 1:
           for rec in records.values():
               trgSymbols = rec.trgSymbols
               if len(trgSymbols) == 1:
                   lexCounts.addPair(src_symbols[0], trgSymbols[0], rec.counts.co)
        lexCounts.filterNBestBySrc(srcWord = src_symbols[0])

def flattenRecords(records, sort = False):
    '''if records are type of dict, return them as a list'''
    if type(records) == dict:
        if sort:
            recordList = []
            for key in sorted(records.keys()):
              recordList.append(records[key])
            return recordList
        else:
            return records.values()
    elif type(records) == list:
        if sort:
            return sorted(records)
        else:
            return records
    else:
        assert False, "Invalid records"

def pivotRecPairs(rows, workset):
    '''combine the source-pivot and pivot-target records for common pivot phrases

    get the list of record pairs in pivotQueue and put the processed data in outQueue

    if workset.method == "prodprob", estimate trans probs by marginalization
    otherwise, calculate them by estimating co-occurrence counts
    '''
    #lexCounts = lex.PairCounter()

    if len(rows) > 0:
        records = {}
        if workset.multi_target:
            multiRecords = {}
            #jointMethod = workset.jointMethod
        for recPair in rows:
            if workset.matchMethod == 'treecomp':
                # pvt1 and pvt2 must be same
                if recPair[0].trg != recPair[1].src:
                    continue
            elif workset.matchMethod == 'symbols':
                if recPair[0].trgSymbols != recPair[1].src_symbols:
                    continue
            trgKey = recPair[1].trg + ' |||'
            if workset.multi_target:
                #strMultiTrg = intern(recPair[1].trg + ' |COL| ' + recPair[0].trg)
                strMultiTrg = recPair[1].trg + ' |COL| ' + recPair[0].trg
                multiKey = strMultiTrg + ' |||'
            if not trgKey in records:
                # source-target record not yet exists, so making new record
                recPivot = workset.Record()
                recPivot.src = recPair[0].src
                recPivot.trg = recPair[1].trg
                records[trgKey] = recPivot
            recPivot = records[trgKey]
            if workset.multi_target:
                recMulti = workset.Record()
                recMulti.src = recPair[0].src
                recMulti.trg = strMultiTrg
                multiRecords[multiKey] = recMulti
            # estimating updated features
            #updateFeatures(recPivot, recPair, workset.method)
            updateFeatures(recPivot, recPair, workset, False)
            # updating the count of phrase pair
            updateCounts(recPivot, recPair, workset.method)
            #updateCounts(recPivot, recPair, workset)
            # merging the word alignments
            mergeAligns(recPivot, recPair)
            if workset.multi_target:
                #updateFeatures(recMulti, recPair, workset.method, multi_target = True, jointMethod = jointMethod)
                updateFeatures(recMulti, recPair, workset, multi_target = True)
                updateCounts(recMulti, recPair, workset.method)
                mergeAligns(recMulti, recPair)
        # at this time, all the source-target records are determined for given source
        if workset.multi_target:
            # copying the estimated features of source-target records to source-target-pivot records
            for multiKey, recMulti in multiRecords.items():
                trgPair = recMulti.trg.split(' |COL| ')
                recPivot = records[trgPair[0]+' |||']
                for featureKey in ['egfl', 'egfp', 'fgel', 'fgep']:
                    recMulti.features['0'+featureKey] = recPivot.features[featureKey]
                if workset.jointMethod == 'independent':
                    # p(src|pvt,trg) ~ 1 - (1 - p(src|pvt))(1 - p(src|trg))
                    recMulti.features['fgep'] = 1 - (1 - recMulti.features['1fgep']) * (1 - recMulti.features['0fgep'])
#        if workset.method != 'prodprob':
#            # find word pairs in phrase pairs and update the counts of word pairs
#            updateWordPairCounts(lexCounts, records)
#            # filtering n-best records by co-occurrence counts
#            if not NOPREFILTER:
#                if workset.nbest > 0:
#                    if len(records) > workset.nbest:
#                        scores = []
#                        for key, rec in records.items():
#                            scores.append( (rec.counts.co, key) )
#                        scores.sort(reverse = True)
#                        bestRecords = {}
#                        for _, key in scores[:workset.nbest]:
#                            bestRecords[key] = records[key]
#                        records = bestRecords
#            # calculate forward phrase trans probs
#            calcPhraseTransProbsByCounts(records)
        # if threshold is set (non-zero), aborting the records having trans probs under it
        if workset.threshold < 0:
            # aborting records for extremely small trans probs
            ignoring = []
            for key, rec in records.items():
                if rec[0]['fgep'] < workset.threshold and rec[0]['egfp'] < workset.threshold:
                    #ignoring.append(pair)
                    ignoring.append(key)
            for key in ignoring:
                del records[key]
        # if limit number of records is set (non-zero), filter the n-best records by forward trans probs
        if workset.nbest > 0:
            if len(records) > workset.nbest:
                scores = []
                for key, rec in records.items():
                    scores.append( (rec.features['egfp'],key) )
                    #scores.append( (rec.features['fgep'],key) )
                scores.sort(reverse = True)
                bestRecords = {}
                for _, key in scores[:workset.nbest]:
                    bestRecords[key] = records[key]
                records = bestRecords
            if workset.multi_target:
                if len(multiRecords) > workset.nbest:
                    # T1-filtering method
                    bestTrgRecords = {}
                    # first, filtering src-pvt-trg records including n-best src-trg records
                    for multiKey, recMulti in multiRecords.items():
                        for rec in records.values():
                            if multiKey.find(rec.trg + ' |COL|') == 0:
                                bestTrgRecords.setdefault(rec.trg, [])
                                bestTrgRecords[rec.trg].append(recMulti)
                    bestMultiRecords = {}
                    # second, filtering n-best by forward joint trans probs
                    for trgKey, multiList in bestTrgRecords.items():
                        bestMultiRec = None
                        bestForwardJointTransProb = 0
                        for multiRec in multiList:
                            if multiRec.features['egfp'] > bestForwardJointTransProb:
                                bestMultiRec = multiRec
                                bestForwardJointTransProb = multiRec.features['egfp']
                        if bestMultiRec:
                            bestMultiRecords[bestMultiRec.trg] = bestMultiRec
                    # filling n-best records by (s->t,s->t,p)
                    scores = []
                    for multiKey, recMulti in multiRecords.items():
                        scores.append( (recMulti.features['0egfp'],recMulti.features['egfp'],multiKey) )
                    scores.sort(reverse = True)
                    for _, _, multiKey in scores:
                        if len(bestMultiRecords) >= workset.nbest:
                            break
                        else:
                            if multiKey in bestMultiRecords:
                                pass
                            else:
                                bestMultiRecords[multiKey] = multiRecords[multiKey]
                    multiRecords = bestMultiRecords
        if workset.multi_target:
            records = multiRecords
        # putting the records into outQueue, and other process will write them in table file
        if records:
            #workset.pivotCount.add( len(records) )
            for trgKey in sorted(records.keys()):
                rec = records[trgKey]
                writeRecord(rec, workset)
    # exiting from while loop
    # terminate also writeRecords process
    #workset.outQueue.put(None)
    #if workset.method != 'prodprob':
    #    lexCounts.filterNBestByTrg()
    #    lex.saveWordPairCounts(workset.tableLexPath, lexCounts)


def writeRecords(fileObj, records):
#  for rec in flattenRecords(records):
  for rec in flattenRecords(records, sort = True):
      if rec.counts.co > 0:
          fileObj.write( rec.to_str() )
          fileObj.write("\n")


def writeRecord(rec, workset):
    '''write the pivoted records in the queue into the table file'''
    if rec:
        if rec.counts.cooc > 0:
            workset.foutPivot.write( rec.to_str() )
            workset.foutPivot.write( "\n" )
            workset.foutPivot.flush()
            workset.numRecSrcTrg += 1
            workset.setPhrasesSrcTrg.add(rec.src)
            for term in rec.srcTerms:
                workset.setWordsSrcTrg.add(term)

def calcLexWeight(rec, lexCounts, reverse = False):
#    minProb = 10 ** -2
    lexWeight = 1
#    alignMapRev = rec.alignMapRev
    if not reverse:
        minProb  = 1 / float(lexCounts.trgCounts["NULL"])
        # for forward probs, using reversed alignment map
        alignMap = rec.alignMapRev
        srcTerms = rec.srcTerms
        trgTerms = rec.trgTerms
    else:
        minProb = 1 / float(lexCounts.srcCounts["NULL"])
        alignMap = rec.alignMap
        srcTerms = rec.trgTerms
        trgTerms = rec.srcTerms
    minProb = MINPROB
    for trgIndex in range(len(trgTerms)):
        trgTerm = trgTerms[trgIndex]
        if trgIndex in alignMap:
            trgSumProb = 0
            srcIndices = alignMap[trgIndex]
            for srcIndex in srcIndices:
                srcTerm = srcTerms[srcIndex]
                if not reverse:
                    lexProb = lexCounts.calcLexProb(srcTerm, trgTerm)
                else:
                    lexProb = lexCounts.calcLexProbRev(trgTerm, srcTerm)
                trgSumProb += lexProb
            if type(rec) == MosesRecord:
                trgProb = trgSumProb / len(srcIndices)
            else:
                trgProb = trgSumProb / (len(srcIndices) + 1)
#            lexWeight *= (trgSumProb / len(srcIndices))
        else:
          if not reverse:
#              lexWeight *= lexCounts.calcLexProb("NULL", trgTerm)
              trgProb = lexCounts.calcLexProb("NULL", trgTerm)
          else:
#              lexWeight *= lexCounts.calcLexProb(trgTerm, "NULL")
              trgProb = lexCounts.calcLexProb(trgTerm, "NULL")
        lexWeight *= max(trgProb, minProb)
    return lexWeight

def calcLexWeights(table_path, lexCounts, savePath, RecordClass = MosesRecord):
    table_file = files.open(table_path, 'r')
    saveFile  = files.open(savePath, 'w')
    for line in table_file:
        rec = RecordClass(line)
        if rec.trg.find('|COL|') < 0:
            rec.features['egfl'] = calcLexWeight(rec, lexCounts, reverse = False)
            rec.features['fgel'] = calcLexWeight(rec, lexCounts, reverse = True)
            saveFile.write( rec.to_str() )
        else:
            rec.features['0egfl'] = calcLexWeight(rec, lexCounts, reverse = False)
            rec.features['0fgel'] = calcLexWeight(rec, lexCounts, reverse = True)
            saveFile.write( rec.to_str() )
    saveFile.close()
    table_file.close()


def pivot(table1, table2, savefile="phrase-table.gz", workdir=".", **options):
    '''find pair of source-pivot and pivot-target records for common pivot phrase'''
    try:
        # initialize the options
        RecordClass = options.get('RecordClass', MosesRecord)
        prefix = options.get('prefix', 'phrase')
        threshold = options.get('threshold', THRESHOLD)
        alignLexPath   = options.get('alignlex', None)
        nbest     = options.get('nbest', NBEST)
        method    = options.get('method', METHOD)
        lexMethod = options.get('lexmethod', LEX_METHOD)
        jointMethod = options.get('jointmethod', JOINT_METHOD)
        matchMethod = options.get('matchmethod', MATCH_METHOD)
        numNulls  = options.get('nulls', NULLS)
        multi_target = options.get('multitarget', False)
        logFile = options.get('log', '')
        showProgress = options.get('progress', True)

        if lexMethod not in ('prodweight', 'table'):
            if alignLexPath == None:
                logging.debug(lexMethod)
                assert False, "aligned lexfile is not given"

        if matchMethod == 'hiero':
            key_type = 'src_hiero'
        else:
            key_type = 'src_symbols'
        logging.log("loading: %s" % table1)
        #tableSrcPvt = Table(table1, RecordClass, key_type=key_type, showProgress=showProgress)
        tableSrcPvt = Table(table1, RecordClass, showProgress=showProgress)
        logging.log("loading: %s" % table2)
        tablePvtTrg = Table(table2, RecordClass, key_type=key_type, showProgress=showProgress)

        workOptions = {}
        workOptions['RecordClass'] = RecordClass
        workOptions['prefix'] = prefix
        workOptions['multi_target'] = multi_target
        workOptions['jointMethod'] = jointMethod
        workOptions['matchMethod'] = matchMethod
        workset = WorkSet(savefile, workdir, method, **workOptions)
        workset.threshold = threshold
        workset.nbest = nbest

        rows = []
        lastSrc = ''
        logging.log("beginning pivot\n")
        #for recSrcPvt in progress.view(tableSrcPvt.find(''),maxCount=len(tableSrcPvt)):
        for recSrcPvt in progress.view(tableSrcPvt.find(''),'processing',max_count=len(tableSrcPvt)):
            src = recSrcPvt.src
            workset.numRecSrcPvt += 1
            workset.setPhrasesSrcPvt.add(recSrcPvt.src)
            for term in recSrcPvt.srcTerms:
                workset.setWordsSrcPvt.add(term)
            if src != lastSrc:
                if len(rows) > 0:
                    pivotRecPairs(rows, workset)
                    rows = []
            #pvtKey = str.join(' ', recSrcPvt.trgSymbols)
            #if key_type == 'src_hiero':
            #    pvtKey = str.join(' ', RecordClass.getSymbols(recSrcPvt.trg,hiero=True))
            #elif key_type == 'src_symbols':
            #    pvtKey = str.join(' ', RecordClass.getSymbols(recSrcPvt.trg,hiero=False))
            #logging.log("pvt key: %s" % (pvtKey,))
            #for recPvtTrg in tablePvtTrg.find(pvtKey):
            #for recPvtTrg in tablePvtTrg.find_src(pvtKey):
            for recPvtTrg in tablePvtTrg.find_src(recSrcPvt.trg):
                workset.numRecPvtTrg += 1
                workset.setPhrasesPvtTrg.add(recPvtTrg.src)
                for term in recPvtTrg.srcTerms:
                    workset.setWordsPvtTrg.add(term)
                rows.append( (recSrcPvt, recPvtTrg) )
            lastSrc = src
        if len(rows) > 0:
            pivotRecPairs(rows, workset)
            rows = []
        if logFile:
            with open(logFile, 'w') as fobj:
                fobj.write("%s = %s\n" % ('numRecSrcPvt', workset.numRecSrcPvt))
                fobj.write("%s = %s\n" % ('uniqPhrasesSrcPvt', len(workset.setPhrasesSrcPvt)))
                fobj.write("%s = %s\n" % ('uniqWordsSrcPvt', len(workset.setWordsSrcPvt)))
                fobj.write("--\n")
                fobj.write("%s = %s\n" % ('numRecPvtTrg', workset.numRecPvtTrg))
                fobj.write("%s = %s\n" % ('uniqPhrasesPvtTrg', len(workset.setPhrasesPvtTrg)))
                fobj.write("%s = %s\n" % ('uniqWordsPvtTrg', len(workset.setWordsPvtTrg)))
                fobj.write("--\n")
                fobj.write("%s = %s\n" % ('numRecSrcTrg', workset.numRecSrcTrg))
                fobj.write("%s = %s\n" % ('uniqPhrasesSrcTrg', len(workset.setPhrasesSrcTrg)))
                fobj.write("%s = %s\n" % ('uniqWordsSrcTrg', len(workset.setWordsSrcTrg)))
                fobj.write("--\n")
                if len(workset.setWordsSrcPvt) != len(workset.setWordsSrcTrg):
                    fobj.write("Lost Words:\n")
                    for word in iter(workset.setWordsSrcPvt - workset.setWordsSrcTrg):
                        fobj.write("\t* \"%s\"\n" % word)
        workset.close()
#        # loading necessary word pair count files
#        if lexMethod != 'prodweight':
#            if lexMethod.find('table') >= 0:
#                if lexMethod.find('+') >= 0:
#                    progress.log("combining lex counts into: %s\n" % (workset.combinedLexPath))
#                    combine_lex.combine_lex(alignLexPath, workset.tableLexPath, workset.combinedLexPath)
#                    progress.log("loading combined word trans probabilities\n")
#                    lexCounts = lex.loadWordPairCounts(workset.combinedLexPath)
#                else:
#                    progress.log("loading table lex: %s\n", workset.tableLexPath)
#                    lexCounts = lex.loadWordPairCounts(workset.tableLexPath)
#                    lexCounts.srcCounts["NULL"] = numNulls
#                    lexCounts.trgCounts["NULL"] = numNulls
#            else:
#                progress.log("loading aligned lex: %s\n" % alignLexPath)
#                lexCounts = lex.loadWordPairCounts(alignLexPath)
##        if workset.method == 'countmin':
#        if method in ['countmin', 'bidirmin', 'bidirgmean', 'bidirmax', 'bidiravr']:
##            # 単語単位の翻訳確率をロードする
##            #progress.log("loading word trans probabilities\n")
##            #lexCounts = lex.loadWordPairCounts(lexPath)
##            progress.log("combining lex counts into: %s\n" % (workset.combinedLexPath))
##            combine_lex.combine_lex(lexPath, workset.tableLexPath, workset.combinedLexPath)
##            progress.log("loading combined word trans probabilities\n")
##            lexCounts = lex.loadWordPairCounts(workset.combinedLexPath)
#            # reversing the table
#            progress.log("reversing %s table into: %s\n" % (prefix, workset.revPath) )
#            reverseTable(workset.pivotPath, workset.revPath, RecordClass)
#            progress.log("reversed %s table\n" % (prefix))
#            # calculating backward phrase trans probs for reversed table
#            progress.log("calculating reversed phrase trans probs into: %s\n" % (workset.trgCountPath))
#            calcPhraseTransProbsOnTable(workset.revPath, workset.trgCountPath, nbest = workset.nbest, RecordClass = RecordClass)
#            progress.log("calculated reversed phrase trans probs\n")
#            # reverseing the reversed table
##            progress.log("reversing %s table into: %s\n" % (prefix,workset.revTrgCountPath))
#            progress.log("reversing %s table into: %s\n" % (prefix,workset.countPath))
##            reverseTable(workset.trgCountPath, workset.revTrgCountPath, RecordClass)
#            reverseTable(workset.trgCountPath, workset.countPath, RecordClass)
#            progress.log("reversed %s table\n" % (prefix))
#            # calculating the forward trans probs
##            progress.log("calculating phrase trans probs into: %s\n" % (workset.countPath))
##            calcPhraseTransProbsOnTable(workset.revTrgCountPath, workset.countPath, nbest = 0, RecordClass = RecordClass)
##            progress.log("calculated phrase trans probs\n")
#            if lexMethod != 'prodweight':
#                # calculating lexical weights
#                progress.log("calculating lex weights into: %s\n" % workset.savePath)
#                calcLexWeights(workset.countPath, lexCounts, workset.savePath, RecordClass)
#                progress.log("calculated lex weights\n")
#            else:
#                progress.log("gzipping into: %s\n" % workset.savePath)
#                files.autoCat(workset.countPath, workset.savePath)
##        elif method == 'prodprob':
#        elif method.find('prodprob') >= 0:
#            if lexMethod != 'prodweight':
#                # calculating lexical weights
#                progress.log("calculating lex weights into: %s\n" % workset.savePath)
#                calcLexWeights(workset.pivotPath, lexCounts, workset.savePath, RecordClass)
#                progress.log("calculated lex weights\n")
#            else:
#                progress.log("gzipping into: %s\n" % workset.savePath)
#                files.autoCat(workset.pivotPath, workset.savePath)
##        elif method == 'multi':
##                progress.log("gzipping into: %s\n" % workset.savePath)
##                files.autoCat(workset.pivotPath, workset.savePath)
#        else:
#            assert False, "Invalid method: %s" % method
    except KeyboardInterrupt:
        # catching exception, finish all the workset processes
        print('')
        print('Caught KeyboardInterrupt, terminating all the worker processes')
        workset.close()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description = 'load 2 rule tables and pivot into one travatar rule table')
    parser.add_argument('table1', help = 'rule table 1')
    parser.add_argument('table2', help = 'rule table 2')
    parser.add_argument('savefile', help = 'path for saving travatar rule table file')
    parser.add_argument('--threshold', help = 'threshold for ignoring the phrase translation probability (real number)', type=float, default=THRESHOLD)
    parser.add_argument('--nbest', help = 'best n scores for rule pair filtering (default = 20)', type=int, default=NBEST)
    parser.add_argument('--method', help = 'triangulation method', choices=method_list, default=METHOD)
    parser.add_argument('--lexmethod', help = 'lexical triangulation method', choices=lex_method_list, default=LEX_METHOD)
    parser.add_argument('--jointmethod', help = 'method to estimate joint trans probs', choices=joint_method_list, default=JOINT_METHOD)
    parser.add_argument('--matchmethod', help = 'matching method', choices=match_method_list, default=MATCH_METHOD)
    parser.add_argument('--workdir', help = 'working directory', default='.')
    parser.add_argument('--alignlex', help = 'word pair counts file', default=None)
    parser.add_argument('--nulls', help = 'number of NULLs (lines) for table lex', type = int, default=NULLS)
    parser.add_argument('--noprefilter', help = 'No pre-filtering', type = bool, default=False)
    parser.add_argument('--multitarget', help = 'enabling multi target model', action='store_true')
    parser.add_argument('--progress', '-p', help = 'show progress', type = bool, default=True)
    parser.add_argument('--log', help = 'log file (optional)', type = str, default='')
    args = vars(parser.parse_args())

    args['RecordClass'] = TravatarRecord
    args['prefix'] = 'rule'
    #base.pivot(**args)
    pivot(**args)

if __name__ == '__main__':
    main()

