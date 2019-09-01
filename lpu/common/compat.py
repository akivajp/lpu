#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''Utility functions for Python 2/3 compatibility'''

import collections
import sys
import types

from lpu.backends import safe_cython as cython

#cdef bytes py2_bytes_to_str(bytes b):
def py2_bytes_to_str(b):
    # as-is
    return b
def py3_bytes_to_str(b):
    #return str(b, 'utf-8', errors='backslashreplace')
    return b.decode('utf-8', 'backslashreplace')

#cdef unicode py2_bytes_to_unicode(bytes b):
def py2_bytes_to_unicode(b):
    return b.decode('utf-8')
#cdef unicode py3_bytes_to_unicode(bytes b):
def py3_bytes_to_unicode(b):
    return b.decode('utf-8')

#cdef bytes py2_str_to_bytes(bytes b):
def py2_str_to_bytes(b):
    # as-is
    return b
#cdef bytes py3_str_to_bytes(str s):
def py3_str_to_bytes(s):
    return s.encode('utf-8', 'backslashreplace')

#cdef unicode py2_str_to_unicode(bytes b):
def py2_str_to_unicode(b):
    return b.decode('utf-8')
#cdef unicode py3_str_to_unicode(str s):
def py3_str_to_unicode(s):
    # as-is
    return unicode(s)

#cdef bytes py2_unicode_to_bytes(unicode u):
def py2_unicode_to_bytes(u):
    return u.encode('utf-8')
#cdef bytes py3_unicode_to_bytes(unicode u):
def py3_unicode_to_bytes(u):
    return u.encode('utf-8')

#cdef bytes py2_unicode_to_str(unicode u):
def py2_unicode_to_str(u):
    return u.encode('utf-8')
def py3_unicode_to_str(u):
    # as-is
    return str(u)

#cdef convert_struct(data, converter_func, fallback_func):
def convert_struct(data, converter_func, fallback_func):
    if isinstance(data, collections.Mapping):
        return type(data)(map(converter_func, data.items()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(converter_func, data))
    else:
        return fallback_func(data)

#cdef bytes py2_to_bytes(s):
def py2_to_bytes(s):
    '''
    convert to byte string
    '''
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return bytes(s)
#cdef bytes py3_to_bytes(s):
def py3_to_bytes(s):
    '''
    convert to byte string
    '''
    if isinstance(s, str):
        return bytes(s, 'utf-8')
    elif isinstance(s, bytes):
        return s
    else:
        return bytes(str(s), 'utf-8')

#cdef bytes py2_to_str(object data):
@cython.locals(dtype = type)
def py2_to_str(data):
    '''
    convert to object based on standard strings
    '''
    #cdef type dtype = type(data)
    dtype = type(data)
    if dtype is str:
        # as-is
        #return str(data)
        return bytes(data)
    elif dtype is unicode:
        return py2_unicode_to_str(data)
    else:
        return bytes(data)
    #if isinstance(data, basestring):
    #    if isinstance(data, unicode):
    #        return data.encode('utf-8')
    #    else:
    #        return data
    ##elif isinstance(data, collections.Mapping):
    ##    return type(data)(map(to_str, data.iteritems()))
    ##elif isinstance(data, collections.Iterable):
    ##    return type(data)(map(to_str, data))
    #else:
    #    return str(data)
#cdef str py3_to_str(data):
@cython.locals(dtype = type)
def py3_to_str(data):
    '''
    convert to object based on standard strings
    '''
    #cdef type dtype = type(data)
    dtype = type(data)
    if dtype is str:
        # as-is
        return data
    elif dtype is bytes:
        return py3_bytes_to_str(data)
    else:
        return str(data)
    #if isinstance(data, str):
    #    return data
    #elif isinstance(data, bytes):
    #    return str(data, 'utf-8')
    #elif isinstance(data, collections.Mapping):
    #    return type(data)(map(to_str, data.items()))
    #elif isinstance(data, collections.Iterable):
    #    return type(data)(map(to_str, data))
    #else:
    #    return str(data)

#cdef unicode py2_to_unicode(data):
@cython.locals(dtype = type)
def py2_to_unicode(data):
    '''
    convert to unicode string
    '''
    #return unicode(s, 'utf-8')
    #cdef type dtype = type(data)
    dtype = type(data)
    if dtype is unicode:
        # as-is
        return data
    elif dtype is bytes:
        return py3_bytes_to_unicode(data)
    else:
        return unicode(data)
    #else:
    #    return convert_struct(data, py2_to_unicode, unicode)
#cdef unicode py3_to_unicode(s):
def py3_to_unicode(s):
    '''
    convert to unicode string
    '''
    if isinstance(s, bytes):
        return str(s, 'utf-8')
    else:
        return str(s)


#cpdef __py3__MethodType(function, instance, cls=None):
def __py3__MethodType(function, instance, cls=None):
#def __py3__MethodType(function, instance, cls):
    # cls (class type) is not used
    return types.MethodType(function, instance)

if sys.version_info.major == 2:
    # Python2
    import itertools
    to_bytes   = py2_to_bytes
    to_str     = py2_to_str
    to_unicode = py2_to_unicode
    bytes_to_str = py2_bytes_to_str
    unicode_to_str = py2_unicode_to_str
    range = xrange
    reduce = reduce
    zip   = itertools.izip
    MethodType = types.MethodType
elif sys.version_info.major == 3:
    # Python3
    import functools
    to_bytes   = py3_to_bytes
    to_str     = py3_to_str
    to_unicode = py3_to_unicode
    bytes_to_str = py3_bytes_to_str
    unicode_to_str = py3_unicode_to_str
    range = range
    reduce = functools.reduce
    zip   = zip
    MethodType = __py3__MethodType
else:
    raise SystemError("Unsupported python version: %s" % sys.version)

