#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Conversion utilities between bytes and str

`lpu.common.files.open` and `lpu.common.progress.FileReader` return either
bytes or str depending on whether the target is gzip-compressed.
The functions here absorb that difference.

These used to live in `lpu.common.compat`, the Python 2/3 compatibility
layer, which is now kept only as a deprecated alias of this module.

bytes と str の相互変換ユーティリティ。

`lpu.common.files.open` や `lpu.common.progress.FileReader` は、対象が
gzip 圧縮ファイルかどうかによって bytes と str のどちらを返すかが変わる。
その差を吸収するための変換関数をここにまとめている。

もともとは Python 2/3 互換レイヤ `lpu.common.compat` が担っていた役割で、
同モジュールは本モジュールへの非推奨エイリアスとして残されている。
'''

from typing import Any

__all__ = ['to_bytes', 'to_str', 'to_unicode']


def to_str(data: Any) -> str:
    r'''Convert any object into str, tolerating decode failures

    bytes are decoded as UTF-8, but invalid byte sequences are escaped with
    ``backslashreplace`` instead of raising. Intended for uses such as log
    output and debug printing, where a conversion failure must not abort
    the process.

    任意のオブジェクトを str に変換する (デコード失敗を許容する)。
    bytes の場合は UTF-8 としてデコードするが、不正なバイト列は
    ``backslashreplace`` でエスケープして例外を投げない。

    Args:
        data: Object to convert; str, bytes or anything else.
            変換対象。str / bytes / その他の任意オブジェクト。

    Returns:
        The converted string. 変換後の文字列。

    Examples:
        >>> to_str('café')
        'café'
        >>> to_str(b'caf\xe9')
        'caf\\xe9'
        >>> to_str(None)
        'None'
    '''
    if isinstance(data, str):
        return data
    if isinstance(data, bytes):
        return data.decode('utf-8', 'backslashreplace')
    return str(data)


def to_unicode(data: Any) -> str:
    r'''Convert any object into str, without tolerating decode failures

    bytes are decoded strictly as UTF-8, so a ``UnicodeDecodeError`` is
    raised for invalid byte sequences. Intended for uses where the encoding
    of the input data should be validated.

    任意のオブジェクトを str に変換する (デコード失敗を許容しない)。
    bytes の場合は UTF-8 として厳密にデコードするため、不正なバイト列に
    対しては ``UnicodeDecodeError`` を送出する。

    Args:
        data: Object to convert; str, bytes or anything else.
            変換対象。str / bytes / その他の任意オブジェクト。

    Returns:
        The converted string. 変換後の文字列。

    Raises:
        UnicodeDecodeError: If bytes cannot be decoded as UTF-8.
            bytes が UTF-8 として解釈できない場合。

    Examples:
        >>> to_unicode('café')
        'café'
        >>> to_unicode(b'caf\xe9')
        Traceback (most recent call last):
            ...
        UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 3: invalid continuation byte
    '''
    if isinstance(data, bytes):
        return str(data, 'utf-8')
    return str(data)


def to_bytes(data: Any) -> bytes:
    r'''Convert any object into UTF-8 encoded bytes

    任意のオブジェクトを UTF-8 の bytes に変換する。

    Args:
        data: Object to convert; str, bytes or anything else.
            変換対象。str / bytes / その他の任意オブジェクト。

    Returns:
        The converted byte string. 変換後のバイト列。

    Examples:
        >>> to_bytes('日本語')
        b'\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e'
        >>> to_bytes(b'raw')
        b'raw'
    '''
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode('utf-8')
    return str(data).encode('utf-8')
