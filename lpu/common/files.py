#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Auxiliary functions for file I/O'''

# Standard libraries
import gzip
import io
import os.path
import sys

# Local libraries
from lpu.common import logging

logger = logging.getLogger(__name__)

#env = os.environ
#env['LC_ALL'] = 'C'

_open = open

if sys.version_info.major >= 3:
    bin_stdin  = sys.stdin.buffer
    bin_stdout = sys.stdout.buffer
    bin_stderr = sys.stderr.buffer
    FileType = io.IOBase
else:
    bin_stdin  = sys.stdin
    bin_stdout = sys.stdout
    bin_stderr = sys.stderr
    FileType = file

def autoCat(filenames, target):
    '''concatenate and copy files into target file (expanding for compressed ones)'''
    if type(filenames) != list:
        filenames = [filenames]
    f_out = open(target, 'w')
    for filename in filenames:
        f_in = open(filename, 'r')
        for line in f_in:
            f_out.write(line)
        f_in.close()
    f_out.close()

def castFile(anyFile):
    '''try to convert any argument to file like object
    * if given file like object, then return itself
    * otherwise (e.g. given file path string), try to open it and return file object'''
    if hasattr(anyFile, 'read'):
        return anyFile
    else:
        return open(anyFile)

def getContentSize(path):
    '''get the file content size (expanded size for compressed one)'''
    try:
        f_in = _open(path, 'rb')
        if is_gzipped(path):
            f_in.seek(-8, 2)
            crc32 = gzip.read32(f_in)
            isize = gzip.read32(f_in)
            f_in.close()
            return isize
        else:
            f_in.seek(0, 2)
            pos = f_in.tell()
            f_in.close()
            return pos
    except Exception as e:
        return -1


def get_ext(filename):
    '''get the extension of given file'''
    (name, ext) = os.path.splitext(filename)
    return ext

#def isIOType(obj):
#    #return isinstance(obj, (io.IOBase,file))
#    return isinstance(obj, FileType)

def is_gzipped(filename):
    '''check whether the given file is compressed by gzip or not'''
    try:
        f = gzip.open(filename, 'r')
        f.readline()
        return True
    except Exception as e:
        return False

def is_mode(fobj, mode):
    if mode in ('r', 'read'):
        return fobj.mode.find('r') >= 0
    elif mode in ('w', 'write'):
        return fobj.mode.find('w') >= 0
    elif mode in ('b', 'binary'):
        if fobj.mode.find('b') >= 0:
            return True
        elif fobj.mode.find('t') >= 0:
            return False
        else:
            return sys.version_info.major < 3
    elif mode in ('t', 'text'):
        if fobj.mode.find('t') >= 0:
            return True
        elif fobj.mode.find('b') >= 0:
            return False
        else:
            return sys.version_info.major >= 3

def load(filename, progress = True, bs = 10 * 1024 * 1024):
    '''load all the content of given file (expand if compressed)'''
    data = io.BytesIO()
    f_in = _open(filename, 'rb')
    if progress:
        print("loading file: '%(filename)s'" % locals())
        c = exp.common.progress.Counter( limit = os.path.getsize(filename) )
    while True:
      buf = f_in.read(bs)
      if not buf:
          break
      else:
          data.write(buf)
          if progress:
              c.count = data.tell()
              if c.should_print():
                  c.update()
                  exp.common.progress.log('loaded (%3.2f%%) : %d bytes' % (c.ratio * 100, c.count))
    f_in.close()
    data.seek(0)
    if progress:
        exp.common.progress.log('loaded (100%%): %d bytes' % (c.count))
        print('')
    if get_ext(filename) == '.gz':
        f_in = gzip.GzipFile(fileobj = data)
        f_in.myfileobj = data
        return f_in
    else:
        return data

def safeMakeDirs(dirpath, **options):
    '''make directories recursively for given path, don't throw exception if directory exists but if file exists'''
    if not os.path.isdir(dirpath):
        logger.debug('making directory: "%s"' % dirpath)
        try:
            os.makedirs(dirpath, **options)
        except:
            logger.debug('cannot make directory: "%s"' % dirpath)

def open(filename, mode = 'r'):
    '''open the plain/compressed file transparently'''
    if get_ext(filename) == '.gz':
        file_obj = gzip.open(filename, mode)
    elif mode.find('r') >= 0 and is_gzipped(filename):
        file_obj = gzip.open(filename, mode)
    else:
        #logger.debug("normal open mode")
        file_obj = _open(filename, mode)
    return file_obj

def rawfile(f):
    if hasattr(f, 'myfileobj'):
        # for archive files such as gzip
        return f.myfileobj
#    if isinstance(f, gzip.GzipFile):
#        return f.myfileobj
    elif hasattr(f, 'buffer'):
        # for buffered files such as utf-8 mode
        #return f.buffer
        # might be duplicated buffer
        return rawfile(f.buffer)
    #elif isIOType(f):
    elif isinstance(f, FileType):
        return f
    else:
        logger.debug(f)
        #logging.debug(type(f))
        #logging.debug(dir(f))
        assert False

def rawsize(f):
    try:
        raw = rawfile(f)
        pos = raw.tell()
        raw.seek(-1, 2)
        size = raw.tell()
        raw.seek(pos, 0)
        return size
    except Exception as e:
        logger.debug(repr(e))
        return -1

def rawremain(f):
    return rawsize(f) - rawtell(f)

def rawtell(fileobj):
    '''get the current position of the opend file, return raw (not expanded) position for compressed'''
    return rawfile(fileobj).tell()

def testFile(path):
    '''test file existence'''
    if os.path.isfile(path):
        return True
    #logger.debug("file does not exist: '%s'" % path)
    raise FileNotFoundError("file does not exist: '%s'" % path)

