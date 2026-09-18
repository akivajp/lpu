#!/usr/bin/env python

'''functions mapping from words/phrases to IDs and vice versa'''

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

# The actual phraseMap object, created on first access.
# phraseMap の実体。初回参照時に生成される
_phrase_map = None

# TwoWayIDMap requires the Cython extension and the `pycedar` package, so
# the import is kept inside TYPE_CHECKING to keep this module importable
# without them.
# TwoWayIDMap は Cython 拡張と pycedar を要求するため、本モジュールを
# それら無しで import 可能に保つべく import は TYPE_CHECKING 内に留める。
if TYPE_CHECKING:
    from lpu.data_structs.trie import TwoWayIDMap


def _get_phrase_map() -> "TwoWayIDMap":
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


def __getattr__(name: str) -> Any:
    '''Provide the module attribute `phraseMap` lazily (PEP 562)

    モジュール属性 `phraseMap` を遅延生成で提供する (PEP 562)。
    '''
    if name == 'phraseMap':
        return _get_phrase_map()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

class StringEnumerator:
    #def __cinit__(self):
    def __init__(self) -> None:
        self.dict_str2id: dict[str, int] = {}
        self.list_id2str: list[str] = []

    def append(self, string: str) -> bool:
        self.str2id(string)
        return True

    def str2id(self, string: str) -> int:
        if string in self.dict_str2id:
            return self.dict_str2id[string]
        else:
            new_id = len(self.list_id2str)
            self.list_id2str.append(string)
            self.dict_str2id[string] = new_id
            return new_id

    def id2str(self, number: int) -> str:
        if 0 <= number and number < len(self.list_id2str):
            return self.list_id2str[number]
        else:
            raise IndexError(f"id {number} is not registered in vocabulary set")

    def ids(self) -> Iterator[int]:
        i = 0
        length = len(self.list_id2str)
        while i < length:
            yield i
            i += 1

    def strings(self) -> Iterator[str]:
        yield from self.list_id2str

    def __iter__(self) -> Iterator[str]:
        return self.strings()

    def __len__(self) -> int:
        return len(self.list_id2str)

word_enum   = StringEnumerator()
phrase_enum = StringEnumerator()

def word2id(word: str) -> int:
    return word_enum.str2id(word)
    #return wordMap[word]

def id2word(number: int) -> str:
    return word_enum.id2str(number)
    #return wordMap.id2str(number)

def phrase2idvec(phrase: str) -> str:
    if not phrase:
        return ''
    #return str.join(',', map(str, map(word2id, phrase.split(' '))))
    #return str.join(',', map(str, map(word2id, phrase.split())))
    return str.join(',', map(str, map(word2id, phrase.strip().split(' '))))

def idvec2phrase(idvec: str) -> str:
    if not idvec:
        return ''
    return str.join(' ', map(id2word, map(int, idvec.split(','))))

def phrase2id(phrase: str) -> int:
    idvec = str.join(',', map(str, map(word2id, phrase.split(' '))))
    return int(_get_phrase_map()[idvec])

def id2phrase(number: int) -> str:
    idvec = _get_phrase_map().id2str(number)
    return str.join(' ', map(id2word, map(int, idvec.split(','))))
