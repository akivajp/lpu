#!/usr/bin/env python

# Standard libraries
from __future__ import annotations

import argparse
import os
import re
import unicodedata
from functools import reduce
from typing import Any

# Local libraries
from lpu.common import logging
from lpu.common import progress
from lpu.common import text

logger = logging.getColorLogger(__name__)

# Escape table for characters that Moses/Travatar style tools use as
# field delimiters.
# Moses/Travatar 系ツールがフィールド区切りに用いる記号のエスケープ表
REPLACE_MAP = {
    '<': '-LT-',
    '>': '-GT-',
    '(': '-LRB-',
    ')': '-RRB-',
    '{': '-LCB-',
    '}': '-RCB-',
    '[': '-LSB-',
    ']': '-RSB-',
    '|': '-BAR-',
    '&': '-AMP-',
    '\t': ' ',
    unicodedata.lookup('ZERO WIDTH SPACE'): ' ',
    unicodedata.lookup('ZERO WIDTH NO-BREAK SPACE'): ' ',
}

def getLongestCommonPrefix(s1: str, s2: str) -> str:
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

def getLongestCommonSuffix(s1: str, s2: str) -> str:
    return getLongestCommonPrefix(s1[::-1],s2[::-1])[::-1]

def replaceChar(c: str) -> str:
    if c in REPLACE_MAP:
        #logging.log("Replacing '%s' -> '%s'" % (c, REPLACE_MAP[c]))
        return REPLACE_MAP[c]
    else:
        return c

def normalize(line: str, escape: bool = False) -> str:
    line = unicodedata.normalize('NFKD', line)
    if escape:
        line = ''.join(map(replaceChar, line))
    line = unicodedata.normalize('NFC', line)
    line = re.sub(r'\s+', ' ', line)
    return line

def checkLength(lines: list[str], minLength: int, maxLength: int) -> bool:
    for line in lines:
        words = line.split()
        if len(words) < minLength: return False
        if len(words) > maxLength: return False
    return True

def getDiff(s: str, prefix: str, suffix: str) -> str:
    if len(suffix) == 0:
        return s[len(prefix):None]
    else:
        return s[len(prefix):-len(suffix)]

def cleanParallel(**args: Any) -> None:
    # デフォルト値は main() の argparse と同一のため、CLI 経由では動作不変。
    # .get() の None を排除し、型チェッカー上も実行時上も後段を安全にする
    srcFilePaths = args.get('srcFilePaths', [])
    #outPrefix = args.get('outfileprefix')
    outTag = args.get('outTag', '')
    minLength = args.get('min', 1)
    maxLength = args.get('max', 80)
    out_dir    = args.get('target_directory', './')

    if not os.path.isdir(out_dir):
        logger.info(f"Making directory: {out_dir}")
        os.makedirs(out_dir)

    srcBaseNames = list( map(os.path.basename, srcFilePaths) )
    commonPrefix = reduce(getLongestCommonPrefix, srcBaseNames)
    commonSuffix = reduce(getLongestCommonSuffix, srcBaseNames)
    logger.info(f"common prefix: '{commonPrefix}'")
    logger.info(f"common suffix: '{commonSuffix}'")
    outPaths = []
    for i, path in enumerate(srcFilePaths):
        if outTag[0:1] != '.':
            outTag = '.' + outTag
        if commonSuffix:
            outPath = path + outTag
        else:
            diff = getDiff(os.path.basename(path), commonPrefix, commonSuffix)
            logger.info(f"suffix {i+1}: {diff}")
            outPath = commonPrefix + outTag + diff
        outPaths.append(os.path.join(out_dir, outPath))
    logger.info("writing cleaned corpora into: {} ...".format(str.join(' ',outPaths)))
    # Read as binary and decode each line strictly as UTF-8.
    # バイナリで読み込み、行ごとに UTF-8 として厳密にデコードする
    infiles  = [open(path,'rb') for path in srcFilePaths]
    outfiles = [open(path, 'w', encoding='utf-8') for path in outPaths]
    infiles[0] = progress.view(infiles[0], header='processing')
    # 対訳の片側だけ行数が多い場合、従来動作どおり短い側で打ち切る
    for i, raw_lines in enumerate(zip(*infiles, strict=False)):
        try:
            lines = [text.to_unicode(line.strip()) for line in raw_lines]
            if args.get('normalize', False):
                escape = args.get('escape', False)
                #lines = list( map(normalize, lines) )
                lines = [normalize(line, escape=escape) for line in lines]
            if checkLength(lines, minLength, maxLength):
                for i, line in enumerate(lines):
                    outfiles[i].write(line)
                    outfiles[i].write("\n")
        except Exception as e:
            #sys.stdout.write("\n")
            logger.warning(f"{e} (Line {i})")

def main() -> None:
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

