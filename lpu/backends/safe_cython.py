#!/usr/bin/env python
# -*- coding: utf-8 -*-
# distutils: language=c++

try:
    import cython
    from cython import *
    available = True
except:
    available = False
    compiled = False

if available:
    compiled = cython.compiled
else:
    # flags
    compiled = False
    # dummy decorators
    def _dummy_decorator_with_arguments(*args, **kwargs):
        def _dummy_decorator(func):
            return func
        return _dummy_decorator
    def _dummy_decorator_without_arguments(func):
        return func
    locals = _dummy_decorator_with_arguments
    # dummy functions
    def _dummy_function(*args, **kwargs):
        pass
    address = _dummy_function
    returns = _dummy_function
    typedef = _dummy_function
    struct = _dummy_function
    # dummy types
    bint = None
    double = None
    float = None
    int = None
    long = None
    longlong = None
    size_t = None
    struct = None
    uchar = None
    uint = None
    ulong = None
