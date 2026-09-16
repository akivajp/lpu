#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''[DEPRECATED] Python 2/3 compatibility layer

LPU became Python 3 only in 0.3.0, so this module has lost its purpose.
It is kept as a thin alias for backward compatibility and is scheduled
for removal in the next major update.

【非推奨】Python 2/3 互換レイヤ。

LPU 0.3.0 で Python 3 専用となったため、本モジュールの役割は失われた。
後方互換のための薄いエイリアスとしてのみ残してあり、次のメジャー更新で
削除する予定である。

Migration guide / 移行先:

===============================  ==========================================
Old / 旧                         New / 新
===============================  ==========================================
``compat.to_str``                ``lpu.common.text.to_str``
``compat.to_unicode``            ``lpu.common.text.to_unicode``
``compat.to_bytes``              ``lpu.common.text.to_bytes``
``compat.bytes_to_str``          ``lpu.common.text.to_str``
``compat.range`` / ``zip``       builtin ``range`` / ``zip``
``compat.reduce``                ``functools.reduce``
``compat.MethodType``            ``types.MethodType``
===============================  ==========================================
'''

import functools
import types
import warnings

from lpu.common.text import to_bytes
from lpu.common.text import to_str
from lpu.common.text import to_unicode

__all__ = [
    'MethodType',
    'range',
    'reduce',
    'to_bytes',
    'to_str',
    'to_unicode',
    'zip',
]

warnings.warn(
    "'lpu.common.compat' is deprecated since LPU 0.3.0 and will be removed "
    "in a future release; use 'lpu.common.text' and the standard library "
    "instead.",
    DeprecationWarning,
    stacklevel=2,
)

# String conversions, delegated to lpu.common.text
# 文字列変換 (lpu.common.text への委譲)
bytes_to_str = to_str
unicode_to_str = to_str
py3_bytes_to_str = to_str
py3_to_str = to_str
py3_to_unicode = to_unicode
py3_to_bytes = to_bytes

# Names that builtins or the standard library already cover on Python 3
# Python 3 では組み込み / 標準ライブラリで足りるもの
range = range
zip = zip
reduce = functools.reduce


def MethodType(function, instance, cls=None):
    '''[DEPRECATED] Wrapper around ``types.MethodType``

    ``cls`` is ignored so that the 3-argument form of Python 2 is accepted.

    【非推奨】``types.MethodType`` のラッパ。
    Python 2 の 3 引数形式を受け付けるため ``cls`` を無視する。
    '''
    return types.MethodType(function, instance)
