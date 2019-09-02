#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''functions for numbers'''

# Standard libraries
import math
import sys

# Local libraries
from lpu.backends import safe_cython as cython
from lpu.common import logging

logger = logging.getColorLogger(__name__)

#cpdef object toNumber(anyNum, float margin = 0):
@cython.locals(num_float = float)
@cython.locals(num_int = long)
def toNumber(num_any, margin=0):
    #cdef float floatNum
    #cdef int intNum
    #cdef long intNum
    #floatNum = float(anyNum)
    num_float = float(num_any)
    #intNum   = int(round(floatNum))
    num_int = int(round(num_float))
    if abs(num_float - num_int) <= margin:
        return num_int
    else:
        return num_float

#cpdef bytes __py2__intToBytes(n, int length, str byteorder='big'):
def __py2__intToBytes(n, length, byteorder='big'):
    assert n >= 0
    strHex = '%x' % n
    if len(strHex) >= length*2:
        raise OverflowError('int too big to convert')
    strDecoded = strHex.zfill(length*2).decode('hex')
    return strDecoded if byteorder == 'big' else strDecoded[::-1]
#cpdef bytes __py3__intToBytes(n, int length, str byteorder='big'):
def __py3__intToBytes(n, length, byteorder='big'):
    return int.to_bytes(n, length, byteorder)

#cpdef __py2__intFromBytes(bytes b, str byteorder='big'):
def __py2__intFromBytes(b, byteorder='big'):
    if byteorder == 'big':
        return int(b.encode('hex'), 16)
    else:
        return int(b[::-1].encode('hex'), 16)
#cpdef __py3__intFromBytes(bytes b, str byteorder='big'):
def __py3__intFromBytes(b, byteorder='big'):
    return int.from_bytes(b, byteorder)

if sys.version_info.major == 2:
    # Python2
    intFromBytes = __py2__intFromBytes
    intToBytes   = __py2__intToBytes
elif sys.version_info.major == 3:
    # Python3
    intFromBytes = __py3__intFromBytes
    intToBytes   = __py3__intToBytes
else:
    raise SystemError("Unsupported python version: %s" % sys.version)
