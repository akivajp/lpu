#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''this module provides globally shared stack of environment'''

# Standard libraries
from __future__ import annotations

import os
from typing import Any, TypeVar

# Local libraries
import logging

logger = logging.getLogger(__name__)

# Each layer maps variable names to their string values; the innermost
# (latest) layer wins during lookups.
# (各層は変数名を文字列値に対応させ、検索時は最も内側の層が優先される)
env_stack: list[dict[str, str]] = []

_StackHolderT = TypeVar('_StackHolderT', bound='StackHolder')

def _safe_debug_print(msg: str) -> None:
    try:
        #logger.debug(msg, stack_info=True)
        logger.debug(msg)
    except Exception:
        pass

def get_env(key: str, default: Any = None, system: bool = True) -> Any:
    '''look up a variable in the stack, then optionally in os.environ

    Note: up to 0.2.x the `default` was returned only when system=False,
    so a lookup that missed returned None with the default arguments.

    スタックを検索し、必要なら os.environ も検索する。
    注意: 0.2.x までは system=False のときだけ `default` を返していたため、
    既定の引数では見つからなかった場合に None が返っていた。

    Args:
        key: Name of the variable. 変数名。
        default: Value to return when the key is not found.
            見つからなかった場合に返す値。
        system: Whether to fall back to os.environ.
            os.environ も参照するかどうか。

    Returns:
        The configured value, or `default`. 設定値、または `default`。
    '''
    for env_dict in env_stack[::-1]:
        if key in env_dict:
            return env_dict[key]
    if system and key in os.environ:
        return os.environ[key]
    return default

class StackHolder(object):
    """Class to manage layer on the stack of environment variables
    
    Returns:
        [type] -- [description]
    """
    def __init__(self, affect_system: bool = True):
        _safe_debug_print('initializing environ stack')
        self.env_layer: dict[str, str] = {}
        env_stack.append(self.env_layer)
        self.back_log: list[tuple[str, bool, str]] = []
        self.affect_system = affect_system
        self.level = len(env_stack)

    def get(self, key: str, default: str = "") -> str:
        """
        Get configuration
        
        Arguments:
            key {[str]} -- name of variable
            default {[str]} -- default variable

        Returns:
            [str] -- configured value
        """
        return self.env_layer.get(key, default)

    def set(self, key: str, value: str) -> None:
        """
        Set new configuration
        
        Arguments:
            key {[str]} -- name of variable
            value {[str]} -- value of variable (must be string)
        """
        prev_exist = False
        prev_value = ''
        if self.affect_system:
            _safe_debug_print("setting %s='%s' in env" % (key, value) )
            if key in os.environ:
                prev_exist = True
                prev_value = os.environ[key]
            self.back_log.append( (key,prev_exist,prev_value) )
            os.environ[key] = value
        self.env_layer[key] = value

    def clear(self):
        if self.back_log:
            for key, prev_exist, prev_value in self.back_log[::-1]:
                if prev_exist:
                    _safe_debug_print("record back %s='%s' to env" % (key, prev_value))
                    if os and os.environ:
                        os.environ[key] = prev_value
                else:
                    _safe_debug_print("unset key from env: %s" % (key,))
                    try:
                        if os and os.environ:
                            os.environ.pop(key)
                    except Exception:
                        # the current exception is logged with its traceback
                        # (発生中の例外がトレースバック込みでログされる)
                        logger.exception("failed to unset a variable from os.environ")
        self.env_layer.clear()
        # note: python2.7 does not have list.clear
        del self.back_log[:]

    def unset(self, key: str) -> None:
        """
        Restore a single variable to the value it had before this layer

        Note: up to 0.2.x this also emptied env_layer and back_log entirely,
        so every other variable tracked by this layer silently lost its
        record and was never restored by clear().

        1 つの変数をこの層に入る前の値へ戻す。
        注意: 0.2.x までは env_layer と back_log 全体も空にしていたため、
        この層が記録していた他の変数の記録が失われ、clear() でも
        復元されなくなっていた。

        Arguments:
            key {[str]} -- name of variable
        """
        found = [t for t in self.back_log if t[0] == key]
        if found:
            _, prev_exist, prev_value = found[0]
            if prev_exist:
                _safe_debug_print("record back %s='%s' to env" % (key, prev_value))
                if os and os.environ:
                    os.environ[key] = prev_value
            else:
                _safe_debug_print("unset key from env: %s" % (key,))
                try:
                    if os and os.environ:
                        os.environ.pop(key)
                except Exception as e:
                    logger.exception(e)
            self.back_log = [t for t in self.back_log if t[0] != key]
        self.env_layer.pop(key, None)

    def __enter__(self):
        logger.debug("entering environ stack")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        _safe_debug_print("exiting from environ stack")
        self.clear()
        # Drop this layer from the shared stack. Without this, env_stack
        # grew monotonically for every layer ever created.
        # 共有スタックからこの層を取り除く。これが無いと env_stack は
        # 生成された層の分だけ単調に増え続けていた。
        try:
            env_stack.remove(self.env_layer)
        except ValueError:
            pass

    def __dealloc__(self):
        _safe_debug_print("deallocating environ stack")
        self.clear()

# The default cannot statically match an arbitrary type[T]; callers passing
# a subclass still get the subclass type back.
# (既定値は任意の type[T] に静的に一致しないため、サブクラスを渡した
#  呼び出し側ではサブクラス型がそのまま返ることを期待する)
def push(Class: type[_StackHolderT] = StackHolder,  # type: ignore[assignment]
         **args: str) -> _StackHolderT:
    #env = StackHolder()
    env = Class()
    for key, val in args.items():
        env.set(key, str(val))
    return env

