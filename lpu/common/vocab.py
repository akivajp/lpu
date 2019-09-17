#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''functions mapping from words/phrases to IDs and vice versa'''

# Local libraries
from lpu.backends import safe_cython as cython
from lpu.data_structs.trie import TwoWayIDMap

#wordMap   = TwoWayIDMap()
#wordMap   = {}
phraseMap = TwoWayIDMap()
#phraseMap = {}

#cdef class StringEnumerator:
class StringEnumerator(object):
    # defined in vocab.pxd
    # cdef dict dict_str2id
    # cdef list list_id2str

    #def __cinit__(self):
    def __init__(self):
        self.dict_str2id = {}
        self.list_id2str = []

    #cpdef bool append(self, str string):
    def append(self, string):
        self.str2id(string)
        return True

    #cpdef long str2id(self, str string):
    @cython.locals(new_id = long)
    def str2id(self, string):
        #cdef long new_id
        if string in self.dict_str2id:
            return self.dict_str2id[string]
        else:
            new_id = len(self.list_id2str)
            self.list_id2str.append(string)
            self.dict_str2id[string] = new_id
            return new_id

    #cpdef str id2str(self, long number):
    def id2str(self, number):
        if 0 <= number and number < len(self.list_id2str):
            return self.list_id2str[number]
        else:
            raise IndexError("id %s is not registered in vocabulary set" % (number,))

    @cython.locals(i = long)
    @cython.locals(length = long)
    def ids(self):
        #cdef long i = 0, length = len(self.list_id2str)
        i = 0
        length = len(self.list_id2str)
        while i < length:
            yield i
            i += 1

    @cython.locals(string = str)
    def strings(self):
        #cdef str string
        for string in self.list_id2str:
            yield string

    def __iter__(self):
        return self.strings()

    def __len__(self):
        return len(self.list_id2str)

#cdef StringEnumerator word_enum   = StringEnumerator()
#cdef StringEnumerator phrase_enum = StringEnumerator()
word_enum   = StringEnumerator()
phrase_enum = StringEnumerator()

#cpdef long word2id(str word):
def word2id(word):
    return word_enum.str2id(word)
    #return wordMap[word]

#cpdef str id2word(long number):
def id2word(number):
    return word_enum.id2str(number)
    #return wordMap.id2str(number)

#cpdef str phrase2idvec(str phrase):
def phrase2idvec(phrase):
    if not phrase:
        return ''
    #return str.join(',', map(str, map(word2id, phrase.split(' '))))
    #return str.join(',', map(str, map(word2id, phrase.split())))
    return str.join(',', map(str, map(word2id, phrase.strip().split(' '))))

#cpdef str idvec2phrase(str idvec):
def idvec2phrase(idvec):
    if not idvec:
        return ''
    return str.join(' ', map(id2word, map(int, idvec.split(','))))

#cpdef long phrase2id(str phrase):
@cython.locals(idvec = str)
def phrase2id(phrase):
    #cdef str idvec = str.join(',', map(str, map(word2id, phrase.split(' '))))
    idvec = str.join(',', map(str, map(word2id, phrase.split(' '))))
    return phraseMap[idvec]

#cpdef str id2phrase(long number):
@cython.locals(idvec = str)
def id2phrase(number):
    #cdef str idvec = phraseMap.id2str(number)
    idvec = phraseMap.id2str(number)
    return str.join(' ', map(id2word, map(int, idvec.split(','))))
