#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''Dictionaries and ID Maps implemented by Double-Array Trie'''

import logging
import sys

# Local libraries
from lpu.backends import safe_cython as cython
from lpu.common import compat

logger = logging.getLogger(__name__)

# 3rd party library
try:
    import pycedar
except Exception as e:
    logger.exception(e)
    logger.error(
        "module 'pycedar' is not found, please install 'pycedar' package\n"
        "(e.g. $ pip install --user pycedar)"
    )
    sys.exit(1)

#cdef class IDMap:
class IDMap(object):
    '''auto mapping class from string to unique int'''
    #cdef object dict
    #cdef list unusedIDs
    #cdef int numEmpty

    #def __cinit__(self):
    def __init__(self):
        #self.trie      = pycedar.trie()
        self.dict      = pycedar.dict()
        self.unusedIDs = list()
        self.numEmpty   = 0

    #cpdef long append(self, str key):
    @cython.locals(n = long)
    def append(self, key):
        #cdef long n = self.str2id(key)
        n = self.str2id(key)
        if not key:
            self.numEmpty = 1
            return 0
        elif n >= 0:
            return n
        else:
            if len(self.unusedIDs) > 0:
                n = self.unusedIDs.pop()
            else:
                n = self.dict.num_keys() + 1
            self.dict[key] = n
            return n

    def ids(self):
        if self.numEmpty > 0:
            yield 0
        for r in self.dict.predict(''):
            yield r.value()

    def items(self):
        if self.numEmpty > 0:
            yield ('', 0)
        for r in self.dict.predict(''):
            yield (r.key(), r.value())

    def keys(self):
        if self.numEmpty > 0:
            yield ''
        for r in self.dict.predict(''):
            yield r.key()

    #cpdef long remove(self, str key):
    @cython.locals(n = long)
    def remove(self, key):
        #cdef long n = self.str2id(key)
        n = self.str2id(key)
        if n == 0:
            self.numEmpty = 0
            return 0
        elif n > 0:
            self.dict.erase(key)
            self.unusedIDs.append(n)
            return n
        else:
            raise KeyError(key)

    #cpdef long str2id(self, str key):
    def str2id(self, key):
        if not key:
            if self.numEmpty > 0:
                return 0
            else:
                return -1
        try:
            return self.dict[key]
        except:
            return -1

    #def __delitem__(self, str key):
    def __delitem__(self, key):
        self.remove(key)
    #def __getitem__(self, str key):
    def __getitem__(self, key):
        return self.append(key)
    #def __has__(self, str key):
    def __has__(self, key):
        return self.str2id(key) >= 0
    def __iter__(self):
        return self.keys()
    def __len__(self):
        return self.dict.num_keys() + self.numEmpty

#cdef class TwoWayIDMap(IDMap):
class TwoWayIDMap(IDMap):
    '''auto mapping class from string to unique int and vice versa'''
    #cdef list keyList
    #cdef deque[string] keyList

    #def __cinit__(self):
    def __init__(self):
        IDMap.__init__(self)
        self.keyList.clear()
        self.keyList.push_back(b'')

    #cpdef long append(self, str key):
    @cython.locals(n = cython.size_t)
    def append(self, key):
        n = IDMap.append(self, key)
        if n >= self.keyList.size():
            self.keyList.push_back(compat.to_bytes(key))
        else:
            #self.keyList[n] = key
            self.keyList[n] = compat.to_bytes(key)
        return n

    #cpdef str id2str(self, long num):
    @cython.locals(key = string)
    def id2str(self, num):
        #cdef object key = self.keyList[num]
        #cdef string key
        if num == 0 and self.numEmpty > 0:
            return ''
        key = self.keyList[num]
        #if key:
        if not key.empty():
            #return key
            return compat.to_str(key)
        else:
            #raise IndexError(key)
            raise IndexError(compat.to_str(key))

    @cython.locals(i = cython.size_t)
    #@cython.locals(k = string)
    #@cython.locals(k = cython.address(string))
    #@cython.locals(k = cython.pointer(string))
    #@cython.locals(k = ref_string)
    def ids(self):
        #cdef long i
        #cdef size_t i
        #cdef string k
        #cdef object k
        #for i, k in enumerate(self.keyList):
        #    if k is not None:
        #        yield i
        if self.numEmpty == 1:
            yield 0
        for i in range(1, self.keyList.size()):
            k = self.keyList[i]
            #k = cython.address(self.keyList[i])
            if not k.empty():
            #if k:
                #yield k
                yield i

    @cython.locals(i = cython.size_t)
    @cython.locals(k = object)
    def items(self):
        #cdef long i
        #cdef size_t i
        #cdef object k
        #for i, k in enumerate(self.keyList):
        #    if k is not None:
        #        yield (k, i)
        for i in range(1, self.keyList.size()):
            k = self.keyList[i]
            if not k.empty():
                #yield (i, k)
                yield (i, compat.to_str(k))

    @cython.locals(i = cython.size_t)
    @cython.locals(k = object)
    def keys(self):
        #cdef long i
        #cdef size_t i
        #cdef object k
        #for k in self.keyList:
        #    if k is not None:
        #        yield k
        for i in range(1, self.keyList.size()):
            k = self.keyList[i]
            if not k.empty():
                #yield k
                yield compat.to_str(k)

    #cpdef void purge(self):
    def purge(self):
        while True:
            #if len(self.keyList) <= 1:
            if self.keyList.size() <= 1:
                break
            #if self.keyList[-1] is None:
            if self.keyList.back().empty():
                #self.keyList.pop()
                self.keyList.pop_back()
            else:
                break

    #cpdef long remove(self, str key):
    @cython.locals(n = long)
    def remove(self, key):
        #cdef long n = IDMap.remove(self, key)
        n = IDMap.remove(self, key)
        if n >= 0:
            #self.keyList[n] = None
            self.keyList[n] = b''
        else:
            raise KeyError(key)

    #def __delitem__(self, str key):
    def __delitem__(self, key):
        self.remove(key)
    #def __getitem__(self, str key):
    def __getitem__(self, key):
        return self.append(key)
    def __iter__(self):
        return self.keys()

#cdef class Dict:
class Dict(object):
    '''mapping class from string to any object'''
    #cdef IDMap idmap
    #cdef list objectList

    #def __cinit__(self):
    def __init__(self):
        self.idmap = IDMap()
        self.objectList = [None]

    #cpdef object get(self, str key, object default=None):
    @cython.locals(n = long)
    def get(self, key, default=None):
        #cdef long n = self.idmap.str2id(key)
        n = self.idmap.str2id(key)
        if n >= 0:
            return self.objectList[n]
        else:
            return default

    #cpdef object remove(self, str key):
    @cython.locals(n = long)
    @cython.locals(value = object)
    def remove(self, key):
        #cdef long n
        #cdef object value
        n = self.idmap.remove(key)
        if n >= 0:
            value = self.objectList[n]
            self.objectList[n] = None
            return value
        else:
            raise KeyError(key)

    #cpdef object setdefault(self, str key, object value):
    def setdefault(self, key, value):
        if key in self:
            return self[key]
        else:
            return self.__set(key, value)
    #cdef object __set(self, str key, object value):
    @cython.locals(n = long)
    def __set(self, key, value):
        #cdef long n = self.idmap.append(key)
        n = self.idmap.append(key)
        if n >= len(self.objectList):
            self.objectList.append(value)
        else:
            self.objectList[n] = value
        return value

    def items(self):
        for key, i in self.idmap.items():
            yield (key, self.objectList[i])

    def keys(self):
        return self.idmap.keys()

    def values(self):
        for i in self.idmap.ids():
            yield self.objectList[i]

    #def __delitem__(self, str key):
    def __delitem__(self, key):
        self.remove(key)
    #def __getitem__(self, str key):
    def __getitem__(self, key):
        if key in self:
            return self.get(key)
        else:
            raise KeyError(key)
    #def __setitem__(self, str key, object value):
    def __setitem__(self, key, value):
        self.__set(key, value)

    #def __has__(self, str key):
    def __has__(self, key):
        if not key:
            raise KeyError(key)
        return key in self.idmap
    def __iter__(self):
        return self.keys()
    def __len__(self):
        return len(self.idmap)
