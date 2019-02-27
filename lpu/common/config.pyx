# distutils: language=c++
# -*- coding: utf-8 -*-
# cython: profile=True

'''Configuration utility class for function settings'''

# C++ setting
from libcpp cimport bool

# Standard libraries
import json
from collections import OrderedDict
from collections import Iterable

# Local libraries
from lpu.common import logging
from lpu.common import validation
from lpu.common.logging import debug_print as dprint

cdef class ConfigData:
    '''Configuration data holder'''
    def __cinit__(self, _base=None, **args):
        if isinstance(_base, Config):
            self.__base = _base.data
        elif isinstance(_base, ConfigData):
            self.__base = _base
        elif isinstance(_base, dict):
            #self.__base = _base
            self.__base = dict2data(_base)
        else:
            self.__base = None
        self.__main = OrderedDict()
        if args:
            self.__main.update(args)

    def __contains__(self, key):
        cdef str first_key, remain_keys
        cdef object main = self.__main
        cdef object base = self.__base
        if isinstance(key, str) and key.find('.') >= 0:
            # chained key access
            try:
                first_key, remain_keys = key.split('.', 1)
                return self.__getitem__(first_key).__contains__(remain_keys)
            except:
                return False
        elif main.__contains__(key):
            return True
        elif base and base.__contains__(key):
            return True
        return False

    #def __getattr__(self, key):
    def __getattr__(self, str key):
        cdef str name
        try:
            return self.__getitem__(key)
        except:
            name = self.__class__.__name__
            raise AttributeError("'%s' object has no attribute '%s'" % (name, key))

    def __getitem__(self, key):
        cdef str msg
        cdef object main
        cdef object base
        cdef object value
        cdef str first_key, remain_keys
        main = self.__main
        if isinstance(key, str):
            if key.find('.') >= 0:
                # chained access key
                first_key, remain_keys = key.split('.', 1)
                return self.__getitem__(first_key).__getitem__(remain_keys)
            # first, check key existence in main dict object
            if key in main:
                return main[key]
            # othwerwise, check key existence in base (parent) dict object
            base = self.__base
            if base and key in base:
                # copy on reading
                value = base[key]
                if isinstance(value, ConfigData):
                    # derive, instead of copying
                    value = ConfigData(value)
                main[key] = value
                return value
                #return base[key]
            raise KeyError(key)
        elif isinstance(key, list):
            return [self[subkey] for subkey in key]
        elif isinstance(key, tuple):
            return tuple(self[subkey] for subkey in key)
        elif isinstance(key, Iterable):
            return (self[subkey] for subkey in key)
        else:
            msg = 'Invalid type of key object is given: {} (expected str or Iterable, but expected: {})'
            raise TypeError(msg.format(repr(key), type(key).__name__))

    def __iter__(self):
        cdef set s
        cdef list l
        cdef str key
        cdef object base = self.__base
        cdef object main = self.__main
        l = list(self.__main)
        s = set(l)
        if base:
            #s.update(base)
            for key in base:
                if key not in s:
                    s.add(key)
                    l.append(key)
        for key in l:
            if not key.startswith('_'):
                yield(key)

    def __len__(self):
        return len(set(self))

    def __repr__(self):
        #cdef str str_base
        cdef str str_params
        cdef str name = self.__class__.__name__
        cdef object main = self.__main
        cdef object base = self.__base
        #if base:
        #    str_base = repr(base)
        #else:
        #    str_base = ""
        str_params = get_key_val_str(main, False)
        if base:
            if str_params:
                return "{}({},{})".format(name, repr(base), str_params)
            else:
                return "{}({})".format(name, repr(base))
        else:
            if str_params:
                return "{}({})".format(name, str_params)
            else:
                return "{}()".format(name)
        #if str_params:
        #    return "%s(%r, %s)" % (name,self.__base,str_params)
        #else:
        #    return "%s(%s)" % (name,self.__base)

    def __setattr__(self, key, val):
        self.__setitem__(key, val)
        #if key.startswith('_'):
        #    raise KeyError('Key should not start with "_": %s' % key)
        #else:
        #    #self.__dict__.__setitem__(key, val)
        #    self.__main.__setitem__(key, val)

    def __setitem__(self, key, val):
        cdef str msg
        cdef object retrieved
        cdef ConfigData conf
        cdef object main = self.__main
        cdef object base = self.__base
        # check the key validity
        if not isinstance(key, str):
            raise TypeError('key value should be type of str, but given: %s' % type(key).__name__)
        elif key.startswith('_'):
            raise KeyError('key should not start with "_": %s' % key)
        # process for chained accessing
        if key.find('.') >= 0:
            # chained access key
            first_key, remain_keys = key.split('.', 1)
            if main.__contains__(first_key):
                retrieved = main.__getitem__(first_key)
                if isinstance(retrieved, ConfigData):
                    retrieved.__setitem__(remain_keys, val)
                else:
                    msg = "retrieved object with key '{}': {}, does not allow chained access with key '{}'"
                    raise KeyError(msg.format(first_key, repr(retrieved), remain_keys))
            elif base and base.__contains__(first_key):
                retrieved = self.__base.__getitem__(first_key)
                if isinstance(retrieved, ConfigData):
                    # deriving as base data
                    conf = ConfigData(retrieved)
                    main.__setitem__(first_key, conf)
                    conf.__setitem__(remain_keys, val)
                else:
                    msg = "retrieved object with key '{}': {}, does not allow chained access with key '{}'"
                    raise KeyError(msg.format(first_key, repr(retrieved), remain_keys))
            else:
                # setting new config data, and continue to chained access
                conf = ConfigData()
                main.__setitem__(first_key, conf)
                conf.__setitem__(remain_keys, val)
        else:
            if isinstance(val, dict):
                val = ConfigData(val)
            main.__setitem__(key, val)

cdef class Config:
    '''Configuration maintenance class'''

    def __cinit__(self, _base = None, **args):
        #self.data = ConfigData(_base)
        self.data = ConfigData(_base=_base)
        if args:
            self.update(args)

    def cast(self, name, typeof):
        val = self.require_any(name)
        if type(val) == typeof:
            return val
        else:
            casted = typeof(val)
            #self.data.__dict__[name] = newVal
            self.data[name] = casted
            return casted

    def has(self, key):
        if type(key) is str:
            return key in self
        elif isinstance(key, Iterable):
            return all(map(self.has, key))
        else:
            raise TypeError("Expected str or iterable type, but given: %s" % type(key).__name__)

    def get(self, key, default = None):
        if type(key) is str:
            if key in self:
                return self[key]
            else:
                return default
        elif isinstance(key, Iterable):
            return [self.get(elem, default) for elem in key]
        else:
            raise TypeError("Expected str or iterable type, but given: %s" % type(key).__name__)

    def items(self):
        for key in self:
            yield key, self[key]

    def load_json(self, str str_json, bool override=True):
        #self.update(json.loads(compat.to_str(strJSON)))
        #uniDict = json.loads(strJSON)
        d = json.loads(str_json, object_pairs_hook=OrderedDict)
        d = flat_dict(d, OrderedDict, True)
        #self.update(compat.to_str(uniDict))
        self.update(d, override)
        return self

    def require(self, name, desc = None, typeOf = None):
        val = self.require_any(name, desc)
        if typeOf:
            self.require_type(name, typeOf)
        return val

    def require_any(self, name, desc = None):
        if name not in self.data:
            if desc:
                raise KeyError('Configuration "%s" (%s) is not defined' % (name, desc))
            else:
                raise KeyError('Configuration "%s" is not defined' % (name))
        return self.data.__getitem__(name)

    def require_type(self, name, typeOf):
        val = self.require_any(name)
        if type(val) != typeOf:
            msg = 'Configuration "%s" should be type of %s, but given %s'
            logging.alert(msg % (name, typeOf, type(val)))
        return val

    def set(self, key, val):
        self[key] = val
        return self[key]

    def setdefault(self, key, val):
        if key not in self:
            return self.set(key, val)
        elif self[key] == None:
            return self.set(key, val)
        else:
            return self[key]

    def to_dict(self, key=None, ordered=False, upstream=False, recursive=True, flat=False):
        cdef type dtype
        cdef ConfigData data = self.data
        if ordered:
            dtype = OrderedDict
        else:
            dtype = dict
        if key:
            data = data[key]
        if flat:
            return flat_dict(data2dict(data, dtype, upstream, recursive), dtype, False)
        else:
            return data2dict(data, dtype, upstream, recursive)

    def to_json(self, key=None, upstream=False, **options):
        cdef object d
        d = self.to_dict(key, True, upstream)
        return json.dumps(d, **options)

    def update(self, _conf = None, _override=True, **args):
        if _conf:
            if _override:
                for key, val in _conf.items():
                    if val != None:
                        #dprint(key)
                        #dprint(val)
                        self[key] = val
            else:
                for key in _conf:
                    if key not in self:
                        self[key] = _conf[key]
        if args:
            self.update(args, _override)

    def __contains__(self, key):
        return self.data.__contains__(key)

    def __getitem__(self, key):
        return self.data.__getitem__(key)

    def __iter__(self):
        return self.data.__iter__()

    def __len__(self):
        return self.data.__len__()

    def __repr__(self):
        cdef type cls
        cdef str name
        cls = self.__class__
        name = cls.__name__
        #strParams = get_key_val_str(vars(self.data), False)
        return "%s(%r)" % (name, self.data)

    def __setitem__(self, key, val):
        self.data.__setitem__(key, val)

# type object is problematic in python 3.6?
#cdef object data2dict(object data, type dtype, bool upstream, bool recursive):
cdef object data2dict(object data, object dtype, bool upstream, bool recursive):
    #dprint("--")
    #dprint(data)
    #dprint(dtype)
    #dprint(upstream)
    #dprint(recursive)
    cdef ConfigData cdata
    if not isinstance(data, ConfigData):
        # as-is
        return data
    cdata = data
    if not recursive:
        if upstream:
            return dtype((key,data[key]) for key in data)
        else:
            return dtype((key,data[key]) for key in cdata.__main)
    else:
        if upstream:
            return dtype((key,data2dict(data[key],dtype,upstream,recursive)) for key in data)
        else:
            #dprint(cdata.__main)
            return dtype((key,data2dict(data[key],dtype,upstream,recursive)) for key in cdata.__main)

cdef object dict2data(object obj):
    cdef object key, value
    cdef ConfigData conf
    if not isinstance(obj, dict):
        # as-is
        return obj
    conf = ConfigData()
    for key, value in obj.items():
        conf[key] = dict2data(value)
    return conf

cdef get_key_val_str(object d, bool verbose):
    if verbose:
        items = ["%s=%r" % (t[0],t[1]) for t in d.items()]
    else:
        items = ["%s=%r" % (t[0],t[1]) for t in d.items() if not t[0].startswith('_')]
    return str.join(', ', items)

cdef list flat_items(object items, str prefix, bool chain_key):
    cdef object flatten = []
    cdef str str_prefix
    cdef str full_key
    if chain_key:
        if prefix:
            str_prefix = prefix + '.'
        else:
            str_prefix = ''
    else:
        str_prefix = ''
    for key, val in items:
        full_key = str_prefix + key
        if isinstance(val, dict):
            flatten += flat_items(val.items(), full_key, chain_key)
        else:
            flatten.append( (full_key,val) )
    return flatten
cdef object flat_dict(object d, type dtype, bool chain_key):
    cdef object flatten = dtype()
    for key, val in flat_items(d.items(), None, chain_key):
        if key not in flatten:
            flatten[key] = val
    return flatten

