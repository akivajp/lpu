# distutils: language=c++
# -*- coding: utf-8 -*-

## C++ setting
#from libcpp cimport bool
from libcpp.string cimport string
#from libcpp.vector cimport vector
from libcpp.deque cimport deque
#from libcpp.list cimport list as stl_list
#ctypedef unsigned char byte

import sys

import logging
logger = logging.getLogger(__name__)

# 3rd party library
try:
    import pycedar
except Exception as e:
    logger.exception(e)
    logger.error("module 'pycedar' is not found, please install 'pycedar' package (e.g. $ pip install --user pycedar)")
    sys.exit(1)

# Local libraries
from lpu.common import compat

'''Dictionaries and ID Maps implemented by Double-Array Trie'''

cdef class IDMap:
    '''auto mapping class from string to unique int'''
    cdef object dict
    cdef list unusedIDs
    cdef int numEmpty

    def __cinit__(self):
        #self.trie      = pycedar.trie()
        self.dict      = pycedar.dict()
        self.unusedIDs = list()
        self.numEmpty   = 0

    cpdef long append(self, str key):
        cdef long n = self.str2id(key)
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

    cpdef long remove(self, str key):
        cdef long n = self.str2id(key)
        if n == 0:
            self.numEmpty = 0
            return 0
        elif n > 0:
            self.dict.erase(key)
            self.unusedIDs.append(n)
            return n
        else:
            raise KeyError(key)

    cpdef long str2id(self, str key):
        if not key:
            if self.numEmpty > 0:
                return 0
            else:
                return -1
        try:
            return self.dict[key]
        except:
            return -1

    def __delitem__(self, str key):
        self.remove(key)
    def __getitem__(self, str key):
        return self.append(key)
    def __has__(self, str key):
        return self.str2id(key) >= 0
    def __iter__(self):
        return self.keys()
    def __len__(self):
        return self.dict.num_keys() + self.numEmpty

cdef class TwoWayIDMap(IDMap):
    '''auto mapping class from string to unique int and vice versa'''
    #cdef list keyList
    cdef deque[string] keyList

    def __cinit__(self):
        IDMap.__init__(self)
        #self.keyList = [None]
        self.keyList.clear()
        self.keyList.push_back(b'')

    cpdef long append(self, str key):
        cdef size_t n = IDMap.append(self, key)
        if n >= self.keyList.size():
            self.keyList.push_back(compat.to_bytes(key))
        else:
            #self.keyList[n] = key
            self.keyList[n] = compat.to_bytes(key)
        return n

    cpdef str id2str(self, long num):
        #cdef object key = self.keyList[num]
        cdef string key
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

    def ids(self):
        #cdef long i
        cdef size_t i
        cdef string k
        #cdef object k
        #for i, k in enumerate(self.keyList):
        #    if k is not None:
        #        yield i
        if self.numEmpty == 1:
            yield 0
        for i in range(1, self.keyList.size()):
            k = self.keyList[i]
            if not k.empty():
                yield k

    def items(self):
        #cdef long i
        cdef size_t i
        cdef object k
        #for i, k in enumerate(self.keyList):
        #    if k is not None:
        #        yield (k, i)
        for i in range(1, self.keyList.size()):
            k = self.keyList[i]
            if not k.empty():
                #yield (i, k)
                yield (i, compat.to_str(k))

    def keys(self):
        #cdef long i
        cdef size_t i
        cdef object k
        #for k in self.keyList:
        #    if k is not None:
        #        yield k
        for i in range(1, self.keyList.size()):
            k = self.keyList[i]
            if not k.empty():
                #yield k
                yield compat.to_str(k)

    cpdef void purge(self):
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

    cpdef long remove(self, str key):
        cdef long n = IDMap.remove(self, key)
        if n >= 0:
            #self.keyList[n] = None
            self.keyList[n] = b''
        else:
            raise KeyError(key)

    def __delitem__(self, str key):
        self.remove(key)
    def __getitem__(self, str key):
        return self.append(key)
    def __iter__(self):
        return self.keys()

cdef class Dict:
    '''mapping class from string to any object'''
    cdef IDMap idmap
    cdef list objectList

    def __cinit__(self):
        self.idmap = IDMap()
        self.objectList = [None]

    cpdef object get(self, str key, object default=None):
        cdef long n = self.idmap.str2id(key)
        if n >= 0:
            return self.objectList[n]
        else:
            return default

    cpdef object remove(self, str key):
        cdef long n
        cdef object value
        n = self.idmap.remove(key)
        if n >= 0:
            value = self.objectList[n]
            self.objectList[n] = None
            return value
        else:
            raise KeyError(key)

    cpdef object setdefault(self, str key, object value):
        if key in self:
            return self[key]
        else:
            return self.__set(key, value)
    cdef object __set(self, str key, object value):
        cdef long n = self.idmap.append(key)
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

    def __delitem__(self, str key):
        self.remove(key)
    def __getitem__(self, str key):
        if key in self:
            return self.get(key)
        else:
            raise KeyError(key)
    def __setitem__(self, str key, object value):
        self.__set(key, value)

    def __has__(self, str key):
        if not key:
            raise KeyError(key)
        return key in self.idmap
    def __iter__(self):
        return self.keys()
    def __len__(self):
        return len(self.idmap)

