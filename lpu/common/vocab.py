#!/usr/bin/env python

'''functions mapping from words/phrases to IDs and vice versa'''

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, TextIO, TypeVar, cast, overload

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


# ---------------------------------------------------------------------------
# Token/ID maps
# トークンと ID の相互変換マップ
# ---------------------------------------------------------------------------

# The default special symbols of `IDMap`, assigned IDs in this order.
# `IDMap` の既定の特殊記号。この順に 0 から ID が割り当てられる。
DEFAULT_SYMBOLS: tuple[tuple[str, str], ...] = (
    ('pad', '<pad>'),
    ('bos', '<s>'),
    ('eos', '</s>'),
    ('unk', '<unk>'),
)

# Bound to the concrete class so that the chainable methods of a subclass
# (e.g. LabelMap.load) keep returning that subclass.
# 派生クラスの連鎖可能なメソッド (LabelMap.load 等) がその派生クラス型を
# 返し続けるよう、具象クラスに束縛する。
_IDMapT = TypeVar('_IDMapT', bound='IDMap')


class IDMap:
    '''A bidirectional map between tokens and IDs, with frequency counts

    Unlike `StringEnumerator`, this map reserves special symbols
    (`<pad>` / `<s>` / `</s>` / `<unk>`), counts how often each token was
    observed, can be truncated to the most frequent tokens, and can be
    saved to / loaded from a plain text file. It depends on the standard
    library alone.

    トークンと ID を相互変換する、頻度計数付きの双方向マップ。
    `StringEnumerator` と異なり、特殊記号 (`<pad>` / `<s>` / `</s>` /
    `<unk>`) を予約し、各トークンの出現頻度を数え、高頻度語のみへの
    切り詰めやテキストファイルへの保存・読み込みが行える。
    標準ライブラリのみに依存する。

    The IDs of the special symbols are also exposed as attributes
    (`self.pad`, `self.bos`, `self.eos`, `self.unk`). An attribute is `None`
    when the map has no such symbol, which is the case for `LabelMap`.

    特殊記号の ID は属性 (`self.pad`, `self.bos`, `self.eos`, `self.unk`)
    としても参照できる。該当の記号を持たない場合 (`LabelMap` など) は
    `None` となる。

    Examples:
        >>> idmap = IDMap()
        >>> idmap.feed_field('the cat sat on the mat')
        >>> idmap.encode('the cat')
        [4, 5]
        >>> idmap.decode([4, 5])
        'the cat'
        >>> idmap.str2id('dog') == idmap.unk
        True
    '''

    def __init__(self, sep: str | None = ' ') -> None:
        '''Create an empty map whose special symbols are already registered

        特殊記号を登録済みの空のマップを生成する。

        Args:
            sep: The separator splitting a field into tokens. `None` treats
                the whole field as a single token.
                フィールドをトークンに分割する区切り文字。`None` の場合は
                フィールド全体を 1 トークンとして扱う。
        '''
        self.sep = sep
        self.list_id2str: list[str] = []
        self.dict_str2id: dict[str, int] = {}
        self.dict_count: dict[str, int] = {}
        # 記号名 -> 表層文字列。ID は属性としても保持する
        self.symbols: dict[str, str] = {}
        # 該当の記号を持たない派生クラスを型安全に扱えるよう None を許す
        self.pad: int | None = None
        self.bos: int | None = None
        self.eos: int | None = None
        self.unk: int | None = None
        self.set_symbols()

    # -- symbols / 特殊記号 -------------------------------------------------

    def set_symbols(self: _IDMapT, extra_symbols: Mapping[str, str] | None = None) -> _IDMapT:
        '''Register the default special symbols, plus any extra ones

        既定の特殊記号と、追加で指定された記号を登録する。

        Symbols must be registered before any corpus is fed, so that they
        occupy the lowest IDs; calling this later only appends the symbols
        that are not registered yet.

        記号は最小の ID を占めるようコーパス投入前に登録する必要がある。
        後から呼んだ場合は、未登録の記号を末尾に追加するだけとなる。

        Args:
            extra_symbols: A mapping of attribute name to surface form,
                e.g. `{'mask': '<mask>'}`.
                属性名から表層文字列への対応。例: `{'mask': '<mask>'}`。

        Returns:
            The map itself, so that calls can be chained.
                呼び出しを連鎖できるよう、マップ自身を返す。
        '''
        symbols = dict(DEFAULT_SYMBOLS)
        if extra_symbols:
            symbols.update(extra_symbols)
        return self._register_symbols(symbols)

    def _register_symbols(self: _IDMapT, symbols: Mapping[str, str]) -> _IDMapT:
        '''Assign an ID and an attribute to each of the given symbols

        与えられた各記号に ID と属性を割り当てる。

        The frequency counter is deliberately left untouched: a special
        symbol is not an observed token, and counting it would let it
        compete with real tokens in `truncate()`.

        頻度カウンタは意図的に更新しない。特殊記号は観測されたトークンでは
        なく、計数すると `truncate()` で実トークンと競合してしまうため。
        '''
        for name, surface in symbols.items():
            setattr(self, name, self._new_id(surface))
        self.symbols.update(symbols)
        return self

    # -- lookup / 参照 ------------------------------------------------------

    def _new_id(self, string: str) -> int:
        '''Return the ID of the string, registering it if it is new

        文字列の ID を返す。未登録の場合は登録した上で返す。
        '''
        index = self.dict_str2id.get(string)
        if index is not None:
            return index
        index = len(self.list_id2str)
        self.list_id2str.append(string)
        self.dict_str2id[string] = index
        return index

    def str2id(self, string: str, growth: bool = False) -> int:
        '''Convert a token to its ID

        トークンを ID に変換する。

        Args:
            string: The token to look up.
                参照するトークン。
            growth: Whether to register the token (and count it) when it is
                not known yet. This is how the vocabulary is built.
                未知のトークンを登録 (かつ計数) するかどうか。
                語彙の構築はこの経路で行う。

        Returns:
            The ID of the token, or the ID of `<unk>` for an unknown token
            when `growth` is false.
                トークンの ID。`growth` が偽で未知のトークンの場合は
                `<unk>` の ID。

        Raises:
            KeyError: If the token is unknown, `growth` is false and the map
                has no `<unk>` symbol.
                未知のトークンで `growth` が偽、かつ `<unk>` を持たない場合。
        '''
        if growth:
            self.dict_count[string] = self.dict_count.get(string, 0) + 1
            return self._new_id(string)
        index = self.dict_str2id.get(string)
        if index is not None:
            return index
        if self.unk is None:
            raise KeyError(f"unknown token {string!r}, and this map has no 'unk' symbol")
        return self.unk

    def id2str(self, index: int) -> str:
        '''Convert an ID to its token

        ID をトークンに変換する。

        Returns:
            The token of the ID, or the surface of `<unk>` for an
            unregistered ID.
                ID に対応するトークン。未登録の ID の場合は `<unk>` の表層。

        Raises:
            IndexError: If the ID is unregistered and the map has no `<unk>`
                symbol.
                未登録の ID で、かつ `<unk>` を持たない場合。
        '''
        if 0 <= index < len(self.list_id2str):
            return self.list_id2str[index]
        if self.unk is None:
            raise IndexError(f"id {index} is not registered in this map")
        return self.list_id2str[self.unk]

    # -- encoding / 符号化 --------------------------------------------------

    def _split(self, string: str) -> list[str]:
        '''Split a field into tokens according to `self.sep`

        `self.sep` に従ってフィールドをトークンに分割する。
        '''
        if self.sep is None:
            return [string]
        return string.split(self.sep)

    def _join(self, tokens: Sequence[str]) -> str:
        '''Join tokens back into a field

        トークン列をフィールドに復元する。

        A `None` separator means "the whole field is one token", so there is
        no separator to join with; a space is used as the readable default.

        区切り文字が `None` の場合は「フィールド全体が 1 トークン」を意味し
        結合すべき区切り文字が無いため、可読な既定値として空白を用いる。
        '''
        return str.join(self.sep if self.sep is not None else ' ', tokens)

    def safe_add_symbols(
        self,
        ids: Iterable[int],
        add_bos: bool = True,
        add_eos: bool = True,
    ) -> list[int]:
        '''Surround an ID sequence with the BOS / EOS symbols

        ID 列を BOS / EOS 記号で囲む。

        A symbol that is already present is not duplicated.
        既に付いている記号は重複して付与しない。

        Raises:
            ValueError: If a requested symbol is not defined in this map.
                要求された記号がこのマップに定義されていない場合。
        '''
        result = list(ids)
        if add_bos:
            if self.bos is None:
                raise ValueError("cannot add BOS: this map has no 'bos' symbol")
            if result[0:1] != [self.bos]:
                result.insert(0, self.bos)
        if add_eos:
            if self.eos is None:
                raise ValueError("cannot add EOS: this map has no 'eos' symbol")
            if result[-1:] != [self.eos]:
                result.append(self.eos)
        return result

    def clean_ids(self, ids: Iterable[int]) -> list[int]:
        '''Strip the BOS / EOS / PAD symbols from an ID sequence

        ID 列から BOS / EOS / PAD 記号を取り除く。

        Everything from the first EOS onwards is dropped, a leading BOS is
        removed, and the trailing PAD run is trimmed.

        最初の EOS 以降を捨て、先頭の BOS を取り除き、末尾に連続する PAD を
        切り詰める。

        Examples:
            >>> idmap = IDMap()
            >>> idmap.clean_ids([idmap.bos, 4, 5, idmap.eos, idmap.pad])
            [4, 5]
        '''
        cleaned = list(ids)
        if self.eos is not None and self.eos in cleaned:
            cleaned = cleaned[:cleaned.index(self.eos)]
        if self.bos is not None and cleaned[0:1] == [self.bos]:
            cleaned.pop(0)
        if self.pad is not None:
            while cleaned[-1:] == [self.pad]:
                cleaned.pop()
        return cleaned

    def encode(self, string: str, add_symbols: bool = False) -> list[int]:
        '''Convert a field into a list of IDs

        フィールドを ID のリストに変換する。

        Args:
            string: The field to encode.
                符号化するフィールド。
            add_symbols: Whether to surround the result with BOS / EOS.
                結果を BOS / EOS で囲むかどうか。

        Returns:
            The IDs of the tokens, where an unknown token becomes `<unk>`.
                各トークンの ID。未知のトークンは `<unk>` になる。
        '''
        ids = [self.str2id(token) for token in self._split(string)]
        if add_symbols:
            return self.safe_add_symbols(ids)
        return ids

    @overload
    def decode(
        self,
        ids: Iterable[int],
        remove_symbols: bool = ...,
        *,
        as_tokens: Literal[False] = ...,
    ) -> str: ...

    @overload
    def decode(
        self,
        ids: Iterable[int],
        remove_symbols: bool = ...,
        *,
        as_tokens: Literal[True],
    ) -> list[str]: ...

    def decode(
        self,
        ids: Iterable[int],
        remove_symbols: bool = True,
        *,
        as_tokens: bool = False,
    ) -> str | list[str]:
        '''Convert a list of IDs back into a field

        ID のリストをフィールドに復元する。

        Args:
            ids: The IDs to decode.
                復号する ID 列。
            remove_symbols: Whether to strip the BOS / EOS / PAD symbols
                first (see `clean_ids`).
                先に BOS / EOS / PAD 記号を取り除くかどうか (`clean_ids` 参照)。
            as_tokens: Whether to return the token list instead of the
                joined field.
                結合したフィールドではなくトークンのリストを返すかどうか。

        Examples:
            >>> idmap = IDMap()
            >>> idmap.feed_field('the cat sat')
            >>> idmap.decode(idmap.encode('the cat', add_symbols=True))
            'the cat'
            >>> idmap.decode([4, 5], as_tokens=True)
            ['the', 'cat']
        '''
        if remove_symbols:
            ids = self.clean_ids(ids)
        tokens = [self.id2str(index) for index in ids]
        if as_tokens:
            return tokens
        return self._join(tokens)

    # -- building / 語彙構築 ------------------------------------------------

    def feed_field(self, string: str) -> None:
        '''Register every token of a field, counting its occurrences

        フィールド中の全トークンを登録し、出現回数を数える。
        '''
        for token in self._split(string):
            self.str2id(token, growth=True)

    def feed_corpus(
        self,
        path: str,
        indices: int | Iterable[int],
        field_sep: str = '\t',
    ) -> int:
        '''Register the tokens of the given columns of a TSV corpus

        TSV コーパスの指定列に含まれるトークンを登録する。

        The file is read line by line (and transparently decompressed when
        it is gzipped), so a corpus larger than memory can be fed.

        ファイルは 1 行ずつ読み込む (gzip 圧縮されていれば透過的に展開する)
        ため、メモリに載らない大きさのコーパスも投入できる。

        Args:
            path: The path of the corpus file.
                コーパスファイルのパス。
            indices: The 0-based column index, or indices, to read.
                読み取る列の 0 始まりの添字 (単一または複数)。
            field_sep: The separator between the columns.
                列の区切り文字。

        Returns:
            The number of non-empty lines fed.
                投入した非空行の数。

        Raises:
            ValueError: If a line has fewer columns than requested.
                要求された列数に満たない行があった場合。
        '''
        target_indices = [indices] if isinstance(indices, int) else list(indices)
        # 本モジュールを軽量に保つため (lpu.common.files はロギング等を
        # 引き込む)、必要になった時点で読み込む
        from lpu.common import files
        fed = 0
        fobj = cast(TextIO, files.open(path, 'rt'))
        with fobj:
            for number, raw_line in enumerate(fobj, start=1):
                # strip() だとタブも削られて列がずれるため改行のみ落とす
                line = raw_line.rstrip('\n')
                if not line:
                    continue
                fields = line.split(field_sep)
                for index in target_indices:
                    if index >= len(fields):
                        raise ValueError(
                            f"{path}:{number}: column index {index} is out of range "
                            f"({len(fields)} columns)"
                        )
                    self.feed_field(fields[index])
                fed += 1
        return fed

    def truncate(self: _IDMapT, vocab_size: int) -> _IDMapT:
        '''Keep only the special symbols and the most frequent tokens

        特殊記号と高頻度のトークンのみを残す。

        The special symbols are always kept and keep their IDs, so the
        resulting size can exceed `vocab_size` when the symbols alone
        already exceed it. Ties in frequency are broken by the token itself,
        so the result does not depend on insertion order.

        特殊記号は常に残り ID も維持されるため、記号だけで `vocab_size` を
        超える場合は結果がそれを上回る。頻度が同じ場合はトークン自身を
        キーとして順序を決めるため、結果は投入順に依存しない。

        Args:
            vocab_size: The target number of entries.
                目標とするエントリ数。

        Returns:
            The map itself, so that calls can be chained.
                呼び出しを連鎖できるよう、マップ自身を返す。
        '''
        symbol_surfaces = set(self.symbols.values())
        # 索引を作り直し、記号 -> 高頻度順の実トークンの順に詰め直す
        self.list_id2str = []
        self.dict_str2id = {}
        self._register_symbols(self.symbols)
        for token, _count in sorted(self.dict_count.items(), key=lambda kv: (-kv[1], kv[0])):
            if token in symbol_surfaces:
                continue
            if len(self) >= vocab_size:
                break
            self._new_id(token)
        return self

    # -- persistence / 永続化 -----------------------------------------------

    def save(self, path: str) -> None:
        '''Save the map as a `<count>\\t<token>` text file, in ID order

        マップを `<件数>\\t<トークン>` 形式のテキストファイルとして
        ID 順に保存する。

        The count of a special symbol is written as 0, since symbols are not
        counted. A token containing a tab or a newline cannot be
        round-tripped through this format.

        特殊記号は計数対象外のため件数 0 として書き出す。タブや改行を含む
        トークンはこの形式では往復できない。
        '''
        symbol_surfaces = set(self.symbols.values())
        with open(path, 'w', encoding='utf-8', newline='\n') as fobj:
            for token in self.list_id2str:
                count = 0 if token in symbol_surfaces else self.dict_count.get(token, 0)
                fobj.write(f"{count}\t{token}\n")

    def load(self: _IDMapT, path: str) -> _IDMapT:
        '''Load the entries of a file saved by `save()` into this map

        `save()` が保存したファイルのエントリをこのマップに読み込む。

        The entries are merged into the current map: a token that is already
        registered (the special symbols, typically) keeps its ID.

        エントリは現在のマップに統合される。既に登録済みのトークン
        (通常は特殊記号) は ID を維持する。

        Raises:
            ValueError: If a line is malformed.
                行の形式が不正な場合。

        Returns:
            The map itself, so that calls can be chained.
                呼び出しを連鎖できるよう、マップ自身を返す。
        '''
        with open(path, encoding='utf-8') as fobj:
            for number, raw_line in enumerate(fobj, start=1):
                line = raw_line.rstrip('\n')
                if not line:
                    continue
                count_text, sep, token = line.partition('\t')
                if not sep:
                    raise ValueError(
                        f"{path}:{number}: expected '<count>\\t<token>', given: {line!r}"
                    )
                try:
                    count = int(count_text)
                except ValueError:
                    raise ValueError(
                        f"{path}:{number}: count is not an integer: {count_text!r}"
                    ) from None
                self._new_id(token)
                self.dict_count[token] = count
        return self

    # -- container protocol / コンテナプロトコル ----------------------------

    @overload
    def __getitem__(self, key: str) -> int: ...

    @overload
    def __getitem__(self, key: int) -> str: ...

    def __getitem__(self, key: str | int) -> int | str:
        '''Look the key up in whichever direction its type implies

        キーの型に応じた向きで参照する。

        Examples:
            >>> idmap = IDMap()
            >>> idmap['<unk>']
            3
            >>> idmap[3]
            '<unk>'
        '''
        if isinstance(key, str):
            return self.str2id(key)
        return self.id2str(key)

    def __contains__(self, string: object) -> bool:
        return string in self.dict_str2id

    def __len__(self) -> int:
        return len(self.list_id2str)

    def __iter__(self) -> Iterator[str]:
        return iter(self.list_id2str)


class LabelMap(IDMap):
    '''An `IDMap` for label fields, supporting weighted multi-labels

    ラベルフィールド向けの `IDMap`。重み付きの複数ラベルを扱える。

    A label field is split on whitespace, and each label may carry an
    explicit weight after a colon (`positive:3 negative:1`). A label without
    a weight counts as 1. A label whose text after the colon is not a number
    is taken as a label name containing a colon.

    ラベルフィールドは空白で分割され、各ラベルはコロンに続けて重みを
    明示できる (`positive:3 negative:1`)。重みを持たないラベルは 1 と
    数える。コロンの後が数値でない場合は、コロンを含むラベル名として扱う。

    Unlike `IDMap`, no special symbols are registered by default, since
    padding and sentence boundaries are meaningless for labels.

    `IDMap` と異なり、既定では特殊記号を登録しない。パディングや文境界は
    ラベルには意味を持たないため。

    Examples:
        >>> labels = LabelMap()
        >>> labels.feed_field('positive negative')
        >>> labels.str2dist('positive')
        [1.0, 0.0]
        >>> labels.str2dist('positive:3 negative:1')
        [0.75, 0.25]
    '''

    def __init__(self, add_unk: bool = False) -> None:
        '''Create an empty label map

        空のラベルマップを生成する。

        Args:
            add_unk: Whether to reserve an `<unk>` label, which absorbs
                unknown labels and any probability mass left over.
                `<unk>` ラベルを予約するかどうか。未知のラベルと、
                余った確率質量の受け皿になる。
        '''
        # super().__init__() から set_symbols() が呼ばれるため先に設定する
        self._add_unk = add_unk
        super().__init__(sep=None)

    def set_symbols(self: _IDMapT, extra_symbols: Mapping[str, str] | None = None) -> _IDMapT:
        '''Register only `<unk>` (when requested) and the extra symbols

        (要求された場合の) `<unk>` と追加の記号のみを登録する。
        '''
        symbols: dict[str, str] = {}
        if getattr(self, '_add_unk', False):
            symbols['unk'] = '<unk>'
        if extra_symbols:
            symbols.update(extra_symbols)
        return self._register_symbols(symbols)

    def _split(self, string: str) -> list[str]:
        '''Split a label field on any run of whitespace

        ラベルフィールドを空白の連続で分割する。
        '''
        return string.split()

    def _parse_labels(self, string: str) -> list[tuple[str, float]]:
        '''Parse a label field into (label, weight) pairs

        ラベルフィールドを (ラベル, 重み) の組に解析する。

        Raises:
            ValueError: If an explicit weight is negative.
                明示された重みが負の場合。
        '''
        parsed: list[tuple[str, float]] = []
        for label in self._split(string):
            name, sep, weight_text = label.partition(':')
            if not sep or not weight_text:
                parsed.append((label, 1.0))
                continue
            try:
                weight = float(weight_text)
            except ValueError:
                # コロンの後が数値でない => 重み指定ではなくラベル名の一部
                parsed.append((label, 1.0))
                continue
            if weight < 0.0:
                raise ValueError(f"label weight must not be negative: {label!r}")
            parsed.append((name, weight))
        return parsed

    def feed_field(self, string: str) -> None:
        '''Register every label of a field, ignoring the weights

        フィールド中の全ラベルを登録する。重みは無視する。
        '''
        for name, _weight in self._parse_labels(string):
            self.str2id(name, growth=True)

    def str2dist(self, string: str) -> list[float]:
        '''Convert a label field into a probability distribution

        ラベルフィールドを確率分布に変換する。

        The weights are accumulated and then normalized so that they sum to
        1. When the map has an `<unk>` label and the weights sum to less
        than 1, the remainder is assigned to `<unk>` instead. An empty field
        yields an all-zero vector.

        重みを累積し、合計が 1 になるよう正規化する。`<unk>` ラベルを持ち
        重みの合計が 1 未満の場合は、残りを `<unk>` に割り当てる。
        空のフィールドは全要素 0 のベクトルになる。

        Unlike `feed_field`, this does not register unknown labels: the
        length of the returned vector must stay constant across calls.

        `feed_field` と異なり未知のラベルを登録しない。返すベクトルの
        長さが呼び出しごとに変わってはならないため。

        Returns:
            A vector of `len(self)` probabilities, in ID order.
                ID 順に並んだ `len(self)` 個の確率のベクトル。
        '''
        dist = [0.0] * len(self)
        total = 0.0
        for name, weight in self._parse_labels(string):
            dist[self.str2id(name)] += weight
            total += weight
        if self.unk is not None and 0.0 < total < 1.0:
            # 残りの確率質量を <unk> が引き受ける
            dist[self.unk] += 1.0 - total
            total = 1.0
        if total > 0.0 and total != 1.0:
            dist = [weight / total for weight in dist]
        return dist

    def str2score(self, string: str) -> float:
        '''Convert a label field into the expected value of its numeric labels

        ラベルフィールドを、数値ラベルの期待値に変換する。

        Labels whose surface form is a number (a rating scale, typically)
        contribute their value weighted by their probability; any other
        label contributes nothing.

        表層が数値であるラベル (通常は評点尺度) が、その確率で重み付けた
        値を寄与する。それ以外のラベルは寄与しない。

        Examples:
            >>> scores = LabelMap()
            >>> scores.feed_field('1 5')
            >>> scores.str2score('1:1 5:1')
            3.0
        '''
        score = 0.0
        # str2dist() は len(self) 個を返すため長さは必ず一致する
        for surface, prob in zip(self.list_id2str, self.str2dist(string), strict=True):
            try:
                value = float(surface)
            except ValueError:
                # 数値でないラベル (記号など) は期待値に寄与しない
                continue
            score += value * prob
        return score
