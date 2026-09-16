#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''Dictionaries and ID Maps implemented by Double-Array Trie'''

# Local libraries
# trie.py handles a C++ std::deque<std::string>, so Cython is mandatory
# here and the cython module is imported directly.
# trie.py は C++ の std::deque<std::string> を扱うため Cython 必須であり、
# cython モジュールを直接 import する
import cython

from lpu.common import text

# 3rd party library
# pycedar is a dependency of this module only; the other lpu modules remain
# usable in environments without it. Since this is imported as a library, it
# must not terminate the process, so an ImportError is raised instead
# (0.2.x called sys.exit(1) here).
# pycedar は本モジュール専用の依存であり、インストールされていない環境でも
# lpu の他のモジュールは利用できる。ライブラリとして import されている以上、
# プロセスを終了させてはならないため ImportError を送出する
# (0.2.x では sys.exit(1) を呼んでいた)。
try:
    import pycedar
except ImportError as exc:
    raise ImportError(
        "module 'pycedar' is required by 'lpu.data_structs.trie' "
        "but not installed; please install it "
        "(e.g. $ pip install 'lpu[smt]' or $ pip install pycedar)"
    ) from exc

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
                n = len(self.dict) + 1
            self.dict[key] = n
            return n

    def ids(self):
        if self.numEmpty > 0:
            yield 0
        # pycedar 0.2 and later provide a dict-compatible API
        # (predict() / node.value() of the 0.1 series were removed).
        # pycedar 0.2 以降は dict 互換 API を持つ
        # (0.1 系の predict() / node.value() は廃止された)
        for value in self.dict.values():
            yield value

    def items(self):
        if self.numEmpty > 0:
            yield ('', 0)
        for key, value in self.dict.items():
            yield (key, value)

    def keys(self):
        if self.numEmpty > 0:
            yield ''
        for key in self.dict.keys():
            yield key

    #cpdef long remove(self, str key):
    @cython.locals(n = long)
    def remove(self, key):
        #cdef long n = self.str2id(key)
        n = self.str2id(key)
        if n == 0:
            self.numEmpty = 0
            return 0
        elif n > 0:
            del self.dict[key]
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
        return len(self.dict) + self.numEmpty

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
            self.keyList.push_back(text.to_bytes(key))
        else:
            #self.keyList[n] = key
            self.keyList[n] = text.to_bytes(key)
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
            return text.to_str(key)
        else:
            #raise IndexError(key)
            raise IndexError(text.to_str(key))

    @cython.locals(i = cython.size_t)
    @cython.locals(k = string)
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
    @cython.locals(k = string)
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
                yield (i, text.to_str(k))

    @cython.locals(i = cython.size_t)
    @cython.locals(k = string)
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
                yield text.to_str(k)

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
