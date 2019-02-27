#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard libraries
import argparse
import random

# Local libraries
from lpu.common import compat
from lpu.common import files
from lpu.common import environ
from lpu.common import logging
from lpu.common import numbers
from lpu.common import progress
from lpu.common.config import Config

logger = logging.getColorLogger(__name__)

def get_valid_indices(conf):
    #indices = set()
    indices = []
    infiles = [files.open(path,'rb') for path in conf.data.inpaths]
    infiles[0] = progress.view(infiles[0], 'loading')
    #for i, lines in enumerate(progress.view(compat.zip(*infiles), 'loading')):
    for i, lines in enumerate(compat.zip(*infiles)):
        try:
            lines = map(compat.to_unicode, lines)
            if conf.data.ignore_empty:
                if all([line.rstrip("\n") for line in lines]):
                        indices.append(i)
            else:
                indices.append(i)
        except Exception as e:
            #sys.stdout.write("\n")
            logger.warning("%s (Line %s)" % (e, i))
    return indices

def random_split(conf, **others):
    conf = Config(conf, **others)
    if not check_config(conf):
        return False

    inpaths = conf.data.inpaths
    prefixes = conf.data.prefixes
    suffixes = conf.data.suffixes
    tags = conf.data.tags
    split_sizes = conf.data.split_sizes

    for i, suffix in enumerate(suffixes):
        if suffix[0:1] == '.':
            suffixes[i] = suffix[1:]

    for path in inpaths:
        files.testFile(path)
    logger.info('building sequence')
    indices = get_valid_indices(conf)
    logger.info('loaded: {} lines'.format(len(indices)))
    if conf.data.seed >= 0:
        random.seed(conf.data.seed)
    logger.info("randomizing sequence")
    random.shuffle(indices)
    split_indices = []
    total_size = 0
    total_factor = 0
    for i, size in enumerate(split_sizes):
        if size == '*':
            total_factor += 1
        else:
            size = float(size)
            if size < 1:
                size = int(len(indices) * size)
            split_sizes[i] = size
            total_size += size
    start = 0
    for size in split_sizes:
        if size == '*':
            size = int( float(len(indices) - total_size) / total_factor )
        else:
            size = int(size)
        split_indices.append( set(indices[start:start+size]) )
        start += size
    split_sizes = list( map(len, split_indices) )
    for inpath, prefix, suffix in zip(inpaths, prefixes, suffixes):
        infile = files.open(inpath, 'rb')
        outpaths = []
        for tag in tags:
            if suffix:
                outpath = "%s%s.%s" % (prefix, tag, suffix)
            else:
                outpath = "%s%s" % (prefix, tag)
            outpaths.append(outpath)
        logger.info("writing lines into splitted files: %s" % outpaths)
        logger.info("split sizes: %s" % split_sizes)
        outfiles = [files.open(outpath,'wb') for outpath in outpaths]
        reader = progress.FileReader(infile, 'processing').read_byte_lines()
        #for line_index, line in enumerate(progress.view(infile, 'processing')):
        for line_index, line in enumerate(reader):
            for file_index, outfile in enumerate(outfiles):
                if line_index in split_indices[file_index]:
                    outfile.write(line)
    if conf.data.ids:
        for file_index, tag in enumerate(tags):
            outpath = "%s.%s" % (tag, conf.data.ids)
            if prefix:
                outpath = prefix + outpath
            genIDs = iter(sorted(split_indices[file_index]))
            if progress:
                genIDs = progress.view(genIDs, "Writing IDs into '%s'" % outpath)
            outfile = files.open(outpath, 'wt')
            for line_index in genIDs:
                # line index is zero origin, line id should be +1
                outfile.write("%d\n" % (line_index+1))
    return True

def check_config(conf):
    numInput = len(conf.data.input)
    numTags  = len(conf.data.tags)
    conf.data.inpaths = conf.data.input
    conf.data.seed        = conf.data.random_seed
    conf.data.split_sizes = conf.data.split_sizes
    if not conf.data.prefixes and not conf.data.suffixes:
        logger.warning('at least one of prefixes or suffixes should be given')
        return False
    if not conf.data.prefixes:
        conf.data.prefixes = [''] * numInput
    elif len(conf.data.prefixes) != numInput:
        msg="Number of prefixes should be same with input files (expected %d, but given %d)"
        logger.warning(msg % (numInput, len(conf.data.prefixes)))
        return False
    if not conf.data.suffixes:
        conf.data.suffixes = [''] * numInput
    elif len(conf.data.suffixes) != numInput:
        msg="Number of suffixes should be same with input files (expected %d, but given %d)"
        logger.warning(msg % (numInput, len(conf.data.suffixes)))
        return False
    if len(conf.data.split_sizes) != numTags:
        msg="Number of split sizes should be same with input files (expected %d, but given %d)"
        logger.warning(msg % (numTags, len(conf.data.split_sizes)))
        return False
    for i, size in enumerate(conf.data.split_sizes):
        if size == '*':
            pass
        else:
            try:
                n = float(size)
                conf.data.split_sizes[i] = n
            except Exception as e:
                msg = "string '%s' cannnot be converted to number (given invalid split sizes: %s)"
                logger.warning(msg % (size, conf.data.split_sizes))
            if n <= 0:
                msg = "split size should be positive, but given negative: %s (given invalid split sizes: %s)"
                logger.warning(msg % (n, conf.data.split_sizes))
    logger.debug(conf)
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-I', help='input files', type=str, required=True, nargs='+')
    parser.add_argument('--prefixes', '-P', help='prefixes of splitted files (should be same number with INPUT)', type=str, default=[], nargs='+')
    parser.add_argument('--suffixes', '-S', help='suffixes of splittted files (should be same number with INPUT)', type=str, default=[], nargs='+')
    parser.add_argument('--tags', '-T', help='base names of splitted files (comma separated list)', type=str, required=True, nargs='+')
    parser.add_argument('--split-sizes', '-s', help='number of lines in splitted files (should be same number with TAGS)', type=str, required=True, nargs='+')
    parser.add_argument('--ignore-empty', '-E', help='preventing empty lines to output', action='store_true')
    parser.add_argument('--quiet', '-q', help='not showing staging log', action='store_true')
    parser.add_argument('--debug', '-D', help='verbose mode (including debug info)', action='store_true')
    parser.add_argument('--random-seed', '-R', help='random seed', default=-1, type=int)
    parser.add_argument('--ids', metavar='SUFFIX', help='write original line numbers for each tags', default=0, nargs='?', const='ids')
    args = parser.parse_args()
    conf = Config()
    conf.update(vars(args))
    with logging.using_config(logger) as c:
        if conf.data.debug:
            c.set_debug(True)
            c.set_quiet(False)
        if conf.data.quiet:
            c.set_quiet(True)
            c.set_debug(False)
        logger.debug(conf)
        random_split(conf)

if __name__ == '__main__':
    main()

