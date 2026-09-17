#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''functions for numbers'''

from typing import Literal

# Local libraries
from lpu.common import logging

logger = logging.getColorLogger(__name__)


def toNumber(num_any: float | int | str, margin: float = 0) -> int | float:
    '''convert into int when the value is close enough to an integer

    整数に十分近い値であれば int に変換する。

    Args:
        num_any: Value convertible to float. float に変換可能な値。
        margin: Tolerance for treating the value as an integer.
            整数とみなす許容誤差。

    Returns:
        An int when within the margin, otherwise a float.
            許容誤差内なら int、そうでなければ float。
    '''
    num_float = float(num_any)
    num_int = int(round(num_float))
    if abs(num_float - num_int) <= margin:
        return num_int
    else:
        return num_float


def intToBytes(n: int, length: int, byteorder: Literal['big', 'little'] = 'big') -> bytes:
    '''convert a non-negative int into a byte string of the given length

    非負の int を指定した長さのバイト列に変換する。
    '''
    return int.to_bytes(n, length, byteorder)


def intFromBytes(b: bytes | bytearray, byteorder: Literal['big', 'little'] = 'big') -> int:
    '''convert a byte string back into an int

    バイト列を int に戻す。
    '''
    return int.from_bytes(b, byteorder)
