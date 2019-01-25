# distutils: language=c++
# -*- coding: utf-8 -*-

'''Utility functions for Python 2/3 compatibility'''

import sys
#import collections
import itertools
import types

cdef bytes __py2__to_bytes(s):
    '''
    convert to byte string
    '''
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return bytes(s)
cdef bytes __py3__to_bytes(s):
    '''
    convert to byte string
    '''
    if isinstance(s, str):
        return bytes(s, 'utf-8')
    elif isinstance(s, bytes):
        return s
    else:
        return bytes(str(s), 'utf-8')

cdef str __py2__to_str(data):
    '''
    convert to object based on standard strings
    '''
    if isinstance(data, basestring):
        if isinstance(data, unicode):
            return data.encode('utf-8')
        else:
            return data
    #elif isinstance(data, collections.Mapping):
    #    return type(data)(map(to_str, data.iteritems()))
    #elif isinstance(data, collections.Iterable):
    #    return type(data)(map(to_str, data))
    else:
        return str(data)
cdef str __py3__to_str(data):
    '''
    convert to object based on standard strings
    '''
    if isinstance(data, str):
        return data
    elif isinstance(data, bytes):
        return str(data, 'utf-8')
    #elif isinstance(data, collections.Mapping):
    #    return type(data)(map(to_str, data.items()))
    #elif isinstance(data, collections.Iterable):
    #    return type(data)(map(to_str, data))
    else:
        return str(data)

cpdef unicode __py2__to_unicode(s):
    '''
    convert to unicode string
    '''
    return unicode(s, 'utf-8')
cpdef unicode __py3__to_unicode(s):
    '''
    convert to unicode string
    '''
    if isinstance(s, bytes):
        return str(s, 'utf-8')
    else:
        return str(s)

cpdef __py3__MethodType(function, instance, cls=None):
    # cls (class type) is not used
    return types.MethodType(function, instance)

if sys.version_info.major == 2:
    # Python2
    to_bytes   = __py2__to_bytes
    to_str     = __py2__to_str
    to_unicode = __py2__to_unicode
    range = xrange
    zip   = itertools.izip
    MethodType = types.MethodType
elif sys.version_info.major == 3:
    # Python3
    to_bytes   = __py3__to_bytes
    to_str     = __py3__to_str
    to_unicode = __py3__to_unicode
    range = range
    zip   = zip
    MethodType = __py3__MethodType
else:
    raise SystemError("Unsupported python version: %s" % sys.version)

