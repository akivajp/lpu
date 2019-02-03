# distutils: language=c++
# -*- coding: utf-8 -*-

'''this module provides globally shared stack of environment'''

# C++ setting
from libcpp cimport bool

# Standard libraries
import os

# Local libraries
import lpu
from lpu.__system__ import logging

logger = logging.getLogger(__name__)

env_stack = []

cdef _safe_debug_print(msg):
    try:
        #logger.debug(msg, stack_info=True)
        logger.debug(msg)
    except Exception as e:
        pass

def get_env(key, default=None, system=True):
    for env_dict in env_stack[::-1]:
        if key in env_dict:
            return env_dict[key]
    if system:
        if key in os.environ:
            return os.environ[key]
    else:
        return default

cdef class StackHolder:
    cdef readonly bool affect_system
    cdef readonly int level
    cdef dict env_layer
    cdef list back_log

    def __cinit__(self, affect_system=True):
        _safe_debug_print('initializing environ stack')
        self.env_layer = {}
        env_stack.append(self.env_layer)
        self.back_log = []
        self.affect_system = affect_system
        self.level = len(env_stack)

    cpdef set(self, str key, str value):
        cdef bool prev_exist = False
        cdef str prev_value = ''
        if self.affect_system:
            _safe_debug_print("setting %s='%s' in env" % (key, value) )
            if key in os.environ:
                prev_exist = True
                prev_value = os.environ[key]
            self.back_log.append( (key,prev_exist,prev_value) )
            os.environ[key] = value
        self.env_layer[key] = value

    cpdef clear(self):
        cdef str key
        cdef bool prev_exist
        cdef str prev_value
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
                    except Exception as e:
                        #logging.log(e)
                        #logger.debug(e)
                        pass
        self.env_layer.clear()
        # note: python2.7 does not have list.clear
        del self.back_log[:]

    def __enter__(self):
        logger.debug("entering environ stack")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        _safe_debug_print("exiting from environ stack")
        #logging.debug(exception_type)
        #logging.debug(exception_value)
        #logging.debug(traceback)
        self.clear()

    def __dealloc__(self):
        _safe_debug_print("deallocating environ stack")
        self.clear()

def push(Class=StackHolder, **args):
    #env = StackHolder()
    env = Class()
    for key, val in args.items():
        env.set(key, str(val))
    return env

