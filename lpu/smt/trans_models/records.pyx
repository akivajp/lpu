# distutils: language=c++
# -*- coding: utf-8 -*-

'''classes handling rule table records'''

# Standard libraries
import math

# Local libraries
from lpu.common import compat
from lpu.common import logging
from lpu.common import numbers

# Matching Method
#   tree:    Full Match (Tree Match)
#   tag:     Tag Match (Phrase Structure Match)
#   string:  Symbol String Match (Superficial Match)
MATCH=['tree', 'tag', 'string', 'ftree']

cdef class CoOccurrence:
    cdef public float src, trg, cooc
    def __cinit__(self, float src=0.0, float trg=0.0, float cooc=0):
        self.src  = src
        self.trg  = trg
        self.cooc = cooc

    # calculate P(e|f) (src -> trg)
    cpdef float calcEGFP(self):
        return self.cooc / self.src
    property egfp:
        def __get__(self): return self.calcEGFP()

    # calculate P(f|e) (trg -> src)
    cpdef float calcFGEP(self):
        return self.cooc / self.trg
    property fgep:
        def __get__(self): return self.calcFGEP()

    cpdef CoOccurrence getReversed(self):
        return CoOccurrence(self.trg, self.src, self.cooc)

    cdef void round(self, digits=6):
        self.src  = round(self.src, digits)
        self.trg  = round(self.trg, digits)
        self.cooc = round(self.cooc, digits)

    cpdef void setCounts(self, object src=None, object trg=None, object cooc=None):
        if src:
            self.src = src
        if trg:
            self.trg = trg
        if cooc:
            self.cooc = cooc

    cpdef str to_str(self, float margin = 0):
        cdef str name = self.__class__.__name__
        cdef str mod  = self.__class__.__module__
        cdef str src  = str(numbers.toNumber(self.src,margin))
        cdef str trg  = str(numbers.toNumber(self.trg,margin))
        cdef str cooc = str(numbers.toNumber(self.cooc,margin))
        return "%s.%s(src = %s, trg = %s, cooc = %s)" % (mod, name, src, trg, cooc)

    def __str__(self):
        return self.to_str(0)

cdef class Record(object):
    cdef public str src, trg
    #cdef public long src, trg
    cdef public dict features
    cdef public CoOccurrence counts
    cdef public set aligns
    cdef public object data

    def __cinit__(self):
      self.src = ""
      self.trg = ""
      #self.src = ()
      #self.trg = ()
      #self.src = 0
      #self.trg = 0
      self.features = {}
      self.counts = CoOccurrence()
#      self.aligns = []
      self.aligns = set()

    cpdef fixOrder(self):
        return False

    def getSrcSymbols(self):
        return self.getSymbols(self.src)
    src_symbols = property(getSrcSymbols)

    def getSrcTerms(self):
        return self.getTerms(self.src)
    srcTerms = property(getSrcTerms)

    def getTrgSymbols(self):
        return self.getSymbols(self.trg)
    trgSymbols = property(getTrgSymbols)

    def getTrgTerms(self):
        return self.getTerms(self.trg)
    trgTerms = property(getTrgTerms)

    cpdef getAlignMap(self):
        return getAlignMap(self.aligns, reverse = False)
    #alignMap = property(getAlignMap)
    property alignMap:
        def __get__(self): return self.getAlignMap()

    cpdef getAlignMapRev(self):
        return getAlignMap(self.aligns, reverse = True)
    #alignMapRev = property(getAlignMapRev)
    property alignMapRev:
        def __get__(self): return self.getAlignMapRev()

    cpdef Record getReversed(self):
        cdef Record recRev
        cdef dict revFeatures
        recRev = self.__class__()
        recRev.src = self.trg
        recRev.trg = self.src
        recRev.counts = self.counts.getReversed()
#        debug.log(self.to_str())
#        debug.log(self.aligns)
#        recRev.aligns = getRevAligns(self.aligns)
        recRev.aligns = getRevAlignSet(self.aligns)
        revFeatures = {}
        if 'egfp' in self.features:
            revFeatures[intern('fgep')] = self.features['egfp']
        if 'egfl' in self.features:
            revFeatures[intern('fgel')] = self.features['egfl']
        if 'fgep' in self.features:
            revFeatures[intern('egfp')] = self.features['fgep']
        if 'fgel' in self.features:
            revFeatures[intern('egfl')] = self.features['fgel']
        if 'p' in self.features:
            revFeatures[intern('p')] = self.features['p']
        revFeatures[intern('w')] = len(self.srcTerms)
        recRev.features = revFeatures
        return recRev

    @staticmethod
    def getTerms(phrase):
        if isinstance(phrase, str):
            phrase = phrase.split(' ')
        return phrase

    @staticmethod
    def getSymbols(phrase):
        if isinstance(phrase, str):
            phrase = phrase.split(' ')
        return phrase

class MosesRecord(Record):
    def __init__(self, line = "", delim = '|||'):
        Record.__init__(self)
        self.delim = delim
        self.loadLine(line, delim)

    def loadLine(self, line, delim = '|||'):
        if line:
            fields = line.strip().split(delim)
            self.src = intern( fields[0].strip() )
            self.trg = intern( fields[1].strip() )
            self.features = getMosesFeatures(fields[2])
#            self.aligns = fields[3].strip().split()
            self.aligns = getAlignSet( fields[3] )
            listCounts = getCounts(fields[4])
            self.counts.setCounts(trg = listCounts[0], src = listCounts[1], co = listCounts[2])

#    def getSrcSymbols(self):
#        return self.src.split(' ')
#    src_symbols = property(getSrcSymbols)
#
#    def getSrcTerms(self):
#        return self.src.split(' ')
#    srcTerms = property(getSrcTerms)
#
#    def getTrgSymbols(self):
#        return self.trg.split(' ')
#    trgSymbols = property(getTrgSymbols)
#
#    def getTrgTerms(self):
#        return self.trg.split(' ')
#    trgTerms = property(getTrgTerms)

    def to_str(self, s = ' ||| '):
        strFeatures = getStrMosesFeatures(self.features)
#        strAligns = str.join(' ', self.aligns)
        strAligns = str.join(' ', sorted(self.aligns) )
        self.counts.round()
        strCounts   = "%s %s %s" % (self.counts.trg, self.counts.src, self.counts.cooc)
        #buf = str.join(s, [self.src, self.trg, strFeatures, strAligns, strCounts]) + "\n"
        buf = str.join(s, [self.src, self.trg, strFeatures, strAligns, strCounts])
#        buf = str.join(s, [str(self.src), str(self.trg), strFeatures, strAligns, strCounts]) + "\n"
        return buf

def getAlignMap(aligns, reverse = False):
    alignMap = {}
    for align in aligns:
        (s, t) = map(int, align.split('-'))
        if reverse:
            alignMap.setdefault(t, []).append(s)
        else:
            alignMap.setdefault(s, []).append(t)
    return alignMap

def getAlignSet(strField):
    return set(strField.strip().split())

def getCounts(field):
#    return map(getNumber, field.split())
#    return map(numbers.toNumber, field.split())
    return list(map(numbers.toNumber, field.split()))

def getNumber(anyNum, margin = 0):
    numFloat = float(anyNum)
    numInt = int(round(numFloat))
    if margin > 0:
        if abs(numInt - numFloat) < margin:
            return numInt
        else:
            return numFloat
    elif numFloat == numInt:
        return numInt
    else:
        return numFloat

#def getRevAligns(aligns):
def getRevAlignSet(aligns):
#    revAlignList = []
    revAlignSet = set()
#    debug.log(aligns)
    for a in aligns:
      (s, t) = map(int, a.split('-'))
#      revAlignList.append( "%d-%d" % (t, s) )
      revAlignSet.add( "%d-%d" % (t, s) )
#    return sorted(revAlignList)
    return sorted(revAlignSet)


def getMosesFeatures(field):
    features = {}
    scores = map(getNumber, field.split())
    features[intern('fgep')] = scores[0]
    features[intern('fgel')] = scores[1]
    features[intern('egfp')] = scores[2]
    features[intern('egfl')] = scores[3]
    return features

def getStrMosesFeatures(dicFeatures):
    '''convert back the feature dictionary to score string separated by space'''
    scores = []
    scores.append( dicFeatures.get('fgep', 0) )
    scores.append( dicFeatures.get('fgel', 0) )
    scores.append( dicFeatures.get('egfp', 0) )
    scores.append( dicFeatures.get('egfl', 0) )
    return str.join(' ', map(str,scores))


cdef class TravatarRecord(Record):
    cdef str delim

    def __cinit__(self, object line="", str delim='|||'):
        Record.__init__(self)
        self.delim = delim
        self.loadLine(compat.to_str(line), delim)

#    cpdef getSrcSymbols(self):
#      return getTravatarSymbols(self.src)
#    #src_symbols = property(getSrcSymbols)
#    property src_symbols:
#        def __get__(self): return self.getSrcSymbols()
#
#    cpdef getSrcTerms(self):
#      return getTravatarTerms(self.src)
#    #srcTerms = property(getSrcTerms)
#    property srcTerms:
#        def __get__(self): return self.getSrcTerms()
#
#    cpdef getTrgSymbols(self):
#      return getTravatarSymbols(self.trg)
#    #trgSymbols = property(getTrgSymbols)
#    property trgSymbols:
#        def __get__(self): return self.trgSrcSymbols()
#
#    cpdef getTrgTerms(self):
#      return getTravatarTerms(self.trg)
#    #trgTerms = property(getTrgTerms)
#    property trgTerms:
#        def __get__(self): return self.trgTerms()

    cpdef fixOrder(self):
        cdef str src, trg
        cdef object changed
        src, trg = TravatarRecord.fixOrderStrings(self.src, self.trg)
        changed = bool(src != self.src)
        self.src = src
        self.trg = trg
        return changed

    cpdef TravatarRecord getReversed(self):
      cdef TravatarRecord recRev = TravatarRecord()
      cdef dict revFeatures
      recRev.src = self.trg
      recRev.trg = self.src
      recRev.counts = self.counts.getReversed()
  #    recRev.aligns = record.getRevAligns(self.aligns)
      recRev.aligns = getRevAlignSet(self.aligns)
      revFeatures = {}
      if 'egfp' in self.features:
        revFeatures['fgep'] = self.features['egfp']
      if 'egfl' in self.features:
        revFeatures['fgel'] = self.features['egfl']
      if 'fgep' in self.features:
        revFeatures['egfp'] = self.features['fgep']
      if 'fgel' in self.features:
        revFeatures['egfl'] = self.features['fgel']
      if 'p' in self.features:
        revFeatures['p'] = self.features['p']
      revFeatures['w'] = len(self.srcTerms)
      recRev.features = revFeatures
      return recRev

#    cpdef loadLine(self, str line, str delim = '|||'):
    #def loadLine(self, line, delim = '|||'):
    cpdef loadLine(self, str line, str delim = '|||'):
        cdef list fields
        cdef list listCounts
        if line:
            fields = line.strip().split(delim)
            self.src = fields[0].strip()
            self.trg = fields[1].strip()
            #self.src = vocab.phrase2id(fields[0])
            #self.trg = vocab.phrase2id(fields[1])
            self.features = getTravatarFeatures(fields[2])
            listCounts = getCounts(fields[3])
            if len(listCounts) == 3:
                self.counts.setCounts(cooc = listCounts[0], src = listCounts[1], trg = listCounts[2])
            #self.aligns = fields[4].strip().split()
            self.aligns = getAlignSet( fields[4] )
            #self.data = pd.DataFrame()
            #self.data = pd.Series()

    cpdef syncTags(self):
        self.sync = False
        src_symbols = self.src.split(' ')
        trgSymbols = self.trg.split(' ')
#        if len(src_symbols) >= 4 and src_symbols[0][0] != '"':
        if isTree(src_symbols):
            # src is tree (s-expression)
            if len(trgSymbols) >= 2 and trgSymbols[-2] == "@":
                # trg is tagged
                pass
            else:
                # trg is not tagged
                srcTag = src_symbols[0]
                srcNonTerminals = []
                for s in src_symbols:
                    if s[0:1] == 'x' and s[1:2].isdigit():
                        srcNonTerminals.append(s)
#                        if len(s) > 3:
#                            srcNonTerminals.append(s[3:])
#                        else:
#                            srcNonTerminals.append('X')
                for i, s in enumerate(trgSymbols):
#                    print("TRG SYMBOLS: %s" % s)
                    if s[0:1] == 'x' and s[1:2].isdigit():
#                        print("NONTERMINAL!")
                        if len(s) > 3:
                            # symbol is tagged
                            pass
                        else:
                            # symbol is not tagged
                            index = int(s[1])
                            if self.sync:
                                trgSymbols[i] = srcNonTerminals[index]
                            else:
                                trgSymbols[i] = s + ":X"
#                self.trg = intern(self.trg + " @ " + srcTag)
                trgSymbols.append("@")
                if self.sync:
                    trgSymbols.append(srcTag)
                else:
                    trgSymbols.append('X')
                self.trg = intern(str.join(' ', trgSymbols))
        if len(src_symbols) == 3:
            tag = src_symbols[2]
            if src_symbols[0] == "x0:"+tag:
                # src is unary cycle
                #self.src = ""
                self.src = ()

#    cpdef toDict(self):
#        d = {}
#        d['src'] = self.src
#        d['trg'] = self.trg
#        d['features'] = self.features
#        d['counts'] = self.counts
#        d['aligns'] = self.aligns
#        return d

    cpdef to_str(self, s = ' ||| '):
      strFeatures = getStrTravatarFeatures(self.features)
      self.counts.round()
      strCounts = ""
      if self.counts.cooc > 0:
          #self.counts.cooc = round(self.counts.cooc, 6)
          #strCounts = "%s %s %s" % (self.counts.cooc, self.counts.src, self.counts.trg)
          strCounts = "%s %s %s" % (round(self.counts.cooc,6), round(self.counts.src,6), round(self.counts.trg,6))
  #    strAligns = str.join(' ', self.aligns)
      strAligns = str.join(' ', sorted(self.aligns))
      #buf = str.join(s, [self.src, self.trg, strFeatures, strCounts, strAligns]) + "\n"
      buf = str.join(s, [self.src, self.trg, strFeatures, strCounts, strAligns])
      return buf

    @staticmethod
    def fixOrderStrings(str src, str trg):
        cdef list srcElements = []
        cdef list trgElements = []
        cdef dict replaceDict = {}
        cdef str newSymbol
        cdef object changed = False
        for s in src.split(' '):
            if s[0] == 'x' and s[1].isdigit():
                replaceDict[s[1]] = str(len(replaceDict))
                newSymbol = 'x'+replaceDict[s[1]]+s[2:]
                srcElements.append(newSymbol)
                if s[1] != newSymbol[1]:
                    changed = True
            else:
                # as-is
                srcElements.append(s)
        if not changed:
            return (src, trg)
        for s in trg.split(' '):
            if s[0] == 'x' and s[1].isdigit():
                newSymbol = 'x'+replaceDict[s[1]]+s[2:]
                trgElements.append(newSymbol)
            else:
                # as-is
                trgElements.append(s)
        return (str.join(' ',srcElements), str.join(' ',trgElements))

    @staticmethod
    def getSymbols(rule, hiero=False):
        symbols = []
        for s in rule.split(' '):
          if len(s) < 2:
            if s == "@":
              break
          elif s[0] == '"' and s[-1] == '"':
            symbols.append(s[1:-1])
          elif s[0] == 'x' and s[1].isdigit():
            if len(s) > 3 and not hiero:
              symbols.append('[%s]' % s[3:])
            else:
              symbols.append('[X]')
        return symbols

    @staticmethod
    def getTerms(symbols):
      terms = []
      if type(symbols) == str:
          symbols = symbols.split(' ')
      for s in symbols:
        if len(s) < 2:
          if s == "@":
            break
        elif s[0] == '"' and s[-1] == '"':
          terms.append(s[1:-1])
      return terms

def getFlattenSymbols(symbols, grammar = 'scfg'):
    if isTree(symbols):
        # strSymbols is tree (S-expression)
        newSymbols = []
        tag = symbols[0]
        for s in symbols:
            if s[0:1] == '"':
                newSymbols.append(s)
            elif s[0:1] == "x":
                if grammar == 'scfg':
                    newSymbols.append(s)
                else:
                    fields = s.split(':')
                    newSymbols.append(fields[0]+':X')
        newSymbols.append("@")
        if grammar == 'hiero':
            newSymbols.append('X')
        else:
            newSymbols.append(tag)
        symbols = newSymbols
    return symbols

cpdef str getStrTravatarFeatures(dict dict_features):
    '''convert features dict into string in format of 'key=val' list'''
    cdef list featureList = []
    cdef str key
    cdef object val
    for key, val in dict_features.items():
        if key.find('egf') >= 0 or key.find('fge') >= 0:
            try:
                #val = math.log(val)
                val = round(math.log(val), 6)
            except:
                logging.warn( (key,val) )
        featureList.append( "%s=%s" % (key, val) )
    return str.join(' ', sorted(featureList))

def getTravatarFeatures(field):
  features = {}
  for strKeyVal in field.split():
    #debug.log(strKeyVal)
    (key, val) = strKeyVal.split('=')
    val = getNumber(val)
#    if key in ['egfl', 'egfp', 'fgel', 'fgep']:
#      val = math.e ** val
#    if key[-1] not in ['p', 'w']:
#      val = math.e ** val
    if len(key) >= 4 :
      val = math.e ** val
    features[key] = val
  return features

def isTree(symbols):
#    if len(symbols) >= 4 and symbols[0][0] != '"':
    if len(symbols) >= 4 and symbols[1] == '(':
        return True
    else:
        return False

def syncTags(src_symbols, trgSymbols, sync):
    if isTree(src_symbols):
        # src is tree (s-expression)
        if len(trgSymbols) >= 2 and trgSymbols[-2] == "@":
            # trg is tagged
            pass
        else:
            # trg is not tagged
            srcTag = src_symbols[0]
            srcNonTerminals = []
            for s in src_symbols:
                if s[0:1] == 'x' and s[1:2].isdigit():
                    srcNonTerminals.append(s)
#                        if len(s) > 3:
#                            srcNonTerminals.append(s[3:])
#                        else:
#                            srcNonTerminals.append('X')
            for i, s in enumerate(trgSymbols):
#                    print("TRG SYMBOLS: %s" % s)
                if s[0:1] == 'x' and s[1:2].isdigit():
#                        print("NONTERMINAL!")
                    if len(s) > 3:
                        # symbol is tagged
                        pass
                    else:
                        # symbol is not tagged
                        index = int(s[1])
                        if sync == 'scfg':
                            trgSymbols[i] = srcNonTerminals[index]
                        elif sync == 'hiero':
                            trgSymbols[i] = s + ":X"
#                self.trg = intern(self.trg + " @ " + srcTag)
            trgSymbols.append("@")
            if sync == 'scfg':
                trgSymbols.append(srcTag)
            elif sync == 'hiero':
                trgSymbols.append('X')
#            self.trg = intern(str.join(' ', trgSymbols))
#    if len(src_symbols) == 3:
#        tag = src_symbols[2]
#        if src_symbols[0] == "x0:"+tag:
#            # src is unary cycle
#            self.src = ""
#    print(trgSymbols)
    return src_symbols, trgSymbols

