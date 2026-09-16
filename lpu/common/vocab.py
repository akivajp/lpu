#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''functions mapping from words/phrases to IDs and vice versa'''

# The actual phraseMap object, created on first access.
# phraseMap の実体。初回参照時に生成される
_phrase_map = None


def _get_phrase_map():
    '''Get the ID map for phrases (phraseMap)

    The object is a Double-Array Trie based `TwoWayIDMap`, which requires
    the Cython extension and the `pycedar` package. `StringEnumerator` in
    this module does not depend on them, so the map is created on first
    access rather than at import time.

    フレーズ用 ID マップ (phraseMap) を取得する。
    実体は Double-Array Trie ベースの `TwoWayIDMap` であり、Cython 拡張と
    `pycedar` パッケージを必要とする。本モジュールの `StringEnumerator` は
    それらに依存しないため、import 時ではなく初回参照時に生成する。

    Returns:
        A `TwoWayIDMap` instance converting between phrases and IDs.
            フレーズ文字列と ID を相互変換する `TwoWayIDMap` インスタンス。
    '''
    global _phrase_map
    if _phrase_map is None:
        from lpu.data_structs.trie import TwoWayIDMap
        _phrase_map = TwoWayIDMap()
    return _phrase_map


def __getattr__(name):
    '''Provide the module attribute `phraseMap` lazily (PEP 562)

    モジュール属性 `phraseMap` を遅延生成で提供する (PEP 562)。
    '''
    if name == 'phraseMap':
        return _get_phrase_map()
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))

class StringEnumerator(object):
    #def __cinit__(self):
    def __init__(self):
        self.dict_str2id = {}
        self.list_id2str = []

    def append(self, string):
        self.str2id(string)
        return True

    def str2id(self, string):
        if string in self.dict_str2id:
            return self.dict_str2id[string]
        else:
            new_id = len(self.list_id2str)
            self.list_id2str.append(string)
            self.dict_str2id[string] = new_id
            return new_id

    def id2str(self, number):
        if 0 <= number and number < len(self.list_id2str):
            return self.list_id2str[number]
        else:
            raise IndexError("id %s is not registered in vocabulary set" % (number,))

    def ids(self):
        i = 0
        length = len(self.list_id2str)
        while i < length:
            yield i
            i += 1

    def strings(self):
        for string in self.list_id2str:
            yield string

    def __iter__(self):
        return self.strings()

    def __len__(self):
        return len(self.list_id2str)

word_enum   = StringEnumerator()
phrase_enum = StringEnumerator()

def word2id(word):
    return word_enum.str2id(word)
    #return wordMap[word]

def id2word(number):
    return word_enum.id2str(number)
    #return wordMap.id2str(number)

def phrase2idvec(phrase):
    if not phrase:
        return ''
    #return str.join(',', map(str, map(word2id, phrase.split(' '))))
    #return str.join(',', map(str, map(word2id, phrase.split())))
    return str.join(',', map(str, map(word2id, phrase.strip().split(' '))))

def idvec2phrase(idvec):
    if not idvec:
        return ''
    return str.join(' ', map(id2word, map(int, idvec.split(','))))

def phrase2id(phrase):
    idvec = str.join(',', map(str, map(word2id, phrase.split(' '))))
    return _get_phrase_map()[idvec]

def id2phrase(number):
    idvec = _get_phrase_map().id2str(number)
    return str.join(' ', map(id2word, map(int, idvec.split(','))))
