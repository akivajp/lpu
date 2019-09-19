#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''this module provides globally shared stack of environment'''

# Standard libraries
import os

# Local libraries
from lpu.backends import safe_logging as logging
from lpu.backends import safe_cython as cython

logger = logging.getLogger(__name__)

env_stack = []

def _safe_debug_print(msg):
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

class StackHolder(object):
    """Class to manage layer on the stack of environment variables
    
    Returns:
        [type] -- [description]
    """
    def __init__(self, affect_system=True):
        _safe_debug_print('initializing environ stack')
        self.env_layer = {}
        env_stack.append(self.env_layer)
        self.back_log = []
        self.affect_system = affect_system
        self.level = len(env_stack)

    def get(self, key, default=""):
        """
        Get configuration
        
        Arguments:
            key {[str]} -- name of variable
            default {[str]} -- default variable

        Returns:
            [str] -- configured value
        """
        return self.env_layer.get(key, default)

    #cpdef set(self, str key, str value):
    @cython.locals(prev_exist = bool)
    @cython.locals(prev_value = str)
    def set(self, key, value):
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

    #cpdef clear(self):
    @cython.locals(key = str)
    #@cython.locals(prev_exist = bool)
    @cython.locals(prev_exist = cython.bint)
    @cython.locals(prev_value = str)
    def clear(self):
        #cdef str key
        #cdef bool prev_exist
        #cdef str prev_value
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
                        logger.exception(e)
                        #pass
        self.env_layer.clear()
        # note: python2.7 does not have list.clear
        del self.back_log[:]

    @cython.locals(prev_exist = cython.bint)
    @cython.locals(prev_value = str)
    @cython.locals(found = tuple)
    def unset(self, key):
        if self.back_log:
            #found = next((t[1:] for t in self.back_log if t[0] == key), None)
            found = [t for t in self.back_log if t[0] == key]
            #found = next(t for t in self.back_log if t[0] == key)
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

