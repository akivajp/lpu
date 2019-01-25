# distutils: language=c++
# -*- coding: utf-8 -*-

'''functions mapping from words/phrases to IDs and vice versa'''

# C++ setting
from libcpp cimport bool

# Local libraries
from lpu.data_structs.trie import TwoWayIDMap

#wordMap   = TwoWayIDMap()
#wordMap   = {}
phraseMap = TwoWayIDMap()
#phraseMap = {}

cdef class StringEnumerator:
    # defined in vocab.pxd
    # cdef dict dict_str2id
    # cdef list list_id2str

    def __cinit__(self):
        self.dict_str2id = {}
        self.list_id2str = []

    cpdef bool append(self, str string):
        self.str2id(string)
        return True

    cpdef long str2id(self, str string):
        cdef long new_id
        if string in self.dict_str2id:
            return self.dict_str2id[string]
        else:
            new_id = len(self.list_id2str)
            self.list_id2str.append(string)
            self.dict_str2id[string] = new_id
            return new_id

    cpdef str id2str(self, long number):
        if 0 <= number and number < len(self.list_id2str):
            return self.list_id2str[number]
        else:
            raise IndexError("id %s is not registered in vocabulary set" % (number,))

    def ids(self):
        cdef long i = 0, length = len(self.list_id2str)
        while i < length:
            yield i
            i += 1

    def strings(self):
        cdef str string
        for string in self.list_id2str:
            yield string

    def __iter__(self):
        return self.strings()

    def __len__(self):
        return len(self.list_id2str)

cdef StringEnumerator word_enum   = StringEnumerator()
cdef StringEnumerator phrase_enum = StringEnumerator()

cpdef long word2id(str word):
    return word_enum.str2id(word)
    #return wordMap[word]

cpdef str id2word(long number):
    return word_enum.id2str(number)
    #return wordMap.id2str(number)

cpdef str phrase2idvec(str phrase):
    if not phrase:
        return ''
    #return str.join(',', map(str, map(word2id, phrase.split(' '))))
    #return str.join(',', map(str, map(word2id, phrase.split())))
    return str.join(',', map(str, map(word2id, phrase.strip().split(' '))))

cpdef str idvec2phrase(str idvec):
    if not idvec:
        return ''
    return str.join(' ', map(id2word, map(int, idvec.split(','))))

cpdef long phrase2id(str phrase):
    cdef str idvec = str.join(',', map(str, map(word2id, phrase.split(' '))))
    return phraseMap[idvec]

cpdef str id2phrase(long number):
    cdef str idvec = phraseMap.id2str(number)
    return str.join(' ', map(id2word, map(int, idvec.split(','))))

