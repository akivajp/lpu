#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard libraries
import argparse
import os
import re
import sys
import unicodedata
from functools import reduce

# Local libraries
from lpu.common import compat
from lpu.common import logging
from lpu.common import progress

logger = logging.getColorLogger(__name__)

REPLACE_MAP = {
    compat.to_unicode('<'): compat.to_unicode('-LT-'),
    compat.to_unicode('>'): compat.to_unicode('-GT-'),
    compat.to_unicode('('): compat.to_unicode('-LRB-'),
    compat.to_unicode(')'): compat.to_unicode('-RRB-'),
    compat.to_unicode('{'): compat.to_unicode('-LCB-'),
    compat.to_unicode('}'): compat.to_unicode('-RCB-'),
    compat.to_unicode('['): compat.to_unicode('-LSB-'),
    compat.to_unicode(']'): compat.to_unicode('-RSB-'),
    compat.to_unicode('|'): compat.to_unicode('-BAR-'),
    compat.to_unicode('&'): compat.to_unicode('-AMP-'),
    compat.to_unicode('\t'): compat.to_unicode(' '),
    unicodedata.lookup('ZERO WIDTH SPACE'): compat.to_unicode(' '),
    unicodedata.lookup('ZERO WIDTH NO-BREAK SPACE'): compat.to_unicode(' '),
}

def getLongestCommonPrefix(s1, s2):
    index = 0
    f1 = s1.split('.')
    f2 = s2.split('.')
    while True:
        if len(f1) <= index or len(f2) <= index:
            break
        if f1[index] != f2[index]:
            break
        index += 1
    return str.join('.', f1[0:index])

def getLongestCommonSuffix(s1, s2):
    return getLongestCommonPrefix(s1[::-1],s2[::-1])[::-1]

def replaceChar(c):
    if c in REPLACE_MAP:
        #logging.log("Replacing '%s' -> '%s'" % (c, REPLACE_MAP[c]))
        return REPLACE_MAP[c]
    else:
        return c

def normalize(line, escape=False):
    #line = compat.to_unicode( line.strip() )
    line = unicodedata.normalize('NFKD', line)
    if escape:
        line = compat.to_unicode('').join(map(replaceChar, line))
    line = unicodedata.normalize('NFC', line)
    line = compat.to_str(line)
    line = re.sub(r'\s+', ' ', line)
    return line

def checkLength(lines, minLength, maxLength):
    for line in lines:
        words = line.split()
        if len(words) < minLength: return False
        if len(words) > maxLength: return False
    return True

def getDiff(s, prefix, suffix):
    if len(suffix) == 0:
        return s[len(prefix):None]
    else:
        return s[len(prefix):-len(suffix)]

def cleanParallel(**args):
    srcFilePaths = args.get('srcFilePaths')
    #outPrefix = args.get('outfileprefix')
    outTag = args.get('outTag')
    minLength = args.get('min')
    maxLength = args.get('max')
    out_dir    = args.get('target_directory')

    if not os.path.isdir(out_dir):
        logging.log("Making directory: %s" % out_dir)
        os.makedirs(out_dir)

    #print(args)
    srcBaseNames = list( map(os.path.basename, srcFilePaths) )
    commonPrefix = reduce(getLongestCommonPrefix, srcBaseNames)
    commonSuffix = reduce(getLongestCommonSuffix, srcBaseNames)
    logger.info("common prefix: '{}'".format(commonPrefix))
    logger.info("common suffix: '{}'".format(commonSuffix))
    outPaths = []
    for i, path in enumerate(srcFilePaths):
        if outTag[0:1] != '.':
            outTag = '.' + outTag
        if commonSuffix:
            outPath = path + outTag
        else:
            diff = getDiff(os.path.basename(path), commonPrefix, commonSuffix)
            logger.info("suffix {}: {}".format(i+1, diff))
            outPath = commonPrefix + outTag + diff
        outPaths.append(os.path.join(out_dir, outPath))
    logger.info("writing cleaned corpora into: %s ..." % str.join(' ',outPaths))
    if sys.version_info.major >= 3:
        infiles  = [open(path,'rb') for path in srcFilePaths]
    else:
        infiles  = [open(path,'r') for path in srcFilePaths]
    outfiles = [open(path,'w') for path in outPaths]
    infiles[0] = progress.view(infiles[0], header='processing')
    for i, lines in enumerate(zip(*infiles)):
        try:
            lines = [compat.to_unicode(line.strip()) for line in lines]
            if args.get('normalize'):
                escape = args.get('escape')
                #lines = list( map(normalize, lines) )
                lines = [normalize(line, escape=escape) for line in lines]
            if checkLength(lines, minLength, maxLength):
                for i, line in enumerate(lines):
                    outfiles[i].write(line)
                    outfiles[i].write("\n")
        except Exception as e:
            #sys.stdout.write("\n")
            logging.warn("%s (Line %s)" % (e, i))

def main():
    DEFAULT_MIN_LENGTH = 1
    DEFAULT_MAX_LENGTH = 80
    DEFAULT_RATIO = 9.0
    parser = argparse.ArgumentParser(description='Clean parallel corpus by length and normalize Unicode chars')
    parser.add_argument('srcFilePaths', metavar="filepath", nargs="+", type=str, help='path of file to clean')
    parser.add_argument('outTag', metavar="output_tag", type=str, help='tag added in name of file to save')
    parser.add_argument('--min', default=DEFAULT_MIN_LENGTH, type=int, help='minimum #words per line (default: %(default)s)')
    parser.add_argument('--max', default=DEFAULT_MAX_LENGTH, type=int, help='maximum #words per line (default: %(default)s)')
    parser.add_argument('--ratio', default=DEFAULT_RATIO, type=float, help='upper bound of maximal ratio of #words between each 2 lines (default: %(default)s)')
    parser.add_argument('--target-directory', '-D', default='./', type=str, help='directory to save the cleaned texts (default: %(default)s)')
    parser.add_argument('--escape', action='store_true', help='escape special characters (default: %(default)s)')
    parser.add_argument('--normalize', action='store_true', help='perform unicode normalization (default: %(default)s)')
    #parsed = parser.parse_args(args)
    parsed = parser.parse_args()
    logger.debug(parsed)
    cleanParallel(**vars(parsed))

if __name__ == '__main__':
    main()

