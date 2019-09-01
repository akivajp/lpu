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
    # dummy typedef
    double = None
    float = None
    int = None
    long = None
    longlong = None
    # dummy decorators
    def _dummy_decorator_with_arguments(*args, **kwargs):
        def _dummy_decorator(func):
            return func
    def _dummy_decorator_without_arguments(func):
        return func
    locals = _dummy_decorator_with_arguments
