# distutils: language=c++
# -*- coding: utf-8 -*-
# cython: profile=True

'''Configuration utility class for function settings'''

# Standard libraries
from collections import OrderedDict
from collections import Iterable
import json

# Local libraries
from lpu.backends import safe_cython as cython
from lpu.common import logging
logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

class ConfigData(object):
    '''Configuration data holder'''
    @cython.locals(base = object, main = object)
    def __init__(self, _base=None, **args):
        base = None
        main = None
        if isinstance(_base, Config):
            #self.__base = _base.data
            base = _base.data
        elif isinstance(_base, ConfigData):
            #self.__base = _base
            base = _base
        elif isinstance(_base, dict):
            #self.__base = _base
            #self.__base = dict2data(_base)
            base = dict2data(_base)
        #else:
        #    self.__base = None
        #self.__main = OrderedDict()
        main = OrderedDict()
        if cython.compiled:
            self.__base = base
            self.__main = main
        else:
            dprint(self.__dict__)
            # access from this class
            self.__dict__["_ConfigData__base"] = base
            self.__dict__["_ConfigData__main"] = main
            # access from Config class
            self.__dict__["_Config__base"] = base
            self.__dict__["_Config__main"] = main
            # access from functions
            self.__dict__["__base"] = base
            self.__dict__["__main"] = main
            dprint(self.__dict__)
        if args:
            self.__main.update(args)

    @cython.locals(first_key = str, remain_keys = str)
    @cython.locals(main = object, base = object)
    def __contains__(self, key):
        #cdef str first_key, remain_keys
        #cdef object main = self.__main
        #cdef object base = self.__base
        main = self.__main
        base = self.__base
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

    def __delattr__(self, key):
        if key in self.__main:
            del self.__main[key]
        else:
            name = self.__class__.__name__
            raise AttributeError("'%s' object has no attribute '%s'" % (name, key))

    #def __getattr__(self, key):
    #def __getattr__(self, str key):
    @cython.locals(name = str)
    def __getattr__(self, key):
        #cdef str name
        try:
            return self.__getitem__(key)
        except:
            name = self.__class__.__name__
            dprint(name)
            dprint(key)
            raise AttributeError("'%s' object has no attribute '%s'" % (name, key))

    @cython.locals(msg = str)
    @cython.locals(main = object, base = object, value = object)
    @cython.locals(first_key = str, remain_keys = str)
    def __getitem__(self, key):
        #cdef str msg
        #cdef object main
        #cdef object base
        #cdef object value
        #cdef str first_key, remain_keys
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
                #main[key] = value
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

    @cython.locals(s = set)
    @cython.locals(l = list)
    @cython.locals(key = str)
    @cython.locals(main = object, base = object)
    def __iter__(self):
        #cdef set s
        #cdef list l
        #cdef str key
        #cdef object base = self.__base
        #cdef object main = self.__main
        base = self.__base
        main = self.__main
        l = list()
        s = set()
        #l = list(self.__main)
        #s = set(l)
        if base:
            #s.update(base)
            for key in base:
                s.add(key)
                l.append(key)
        for key in main:
            if key not in s:
                s.add(key)
                l.append(key)
        for key in l:
            if not key.startswith('_'):
                yield(key)

    def __len__(self):
        #return len(set(self))
        return sum(1 for _ in self)

    @cython.locals(str_params = str)
    @cython.locals(name = str)
    @cython.locals(main = object, base = object)
    def __repr__(self):
        #cdef str str_base
        #cdef str str_params
        #cdef str name = self.__class__.__name__
        #cdef object main = self.__main
        #cdef object base = self.__base
        name = self.__class__.__name__
        main = self.__main
        base = self.__base
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

    @cython.locals(msg = str)
    @cython.locals(retrieved = object)
    #@cython.locals(conf = ConfigData)
    @cython.locals(main = object, base = object)
    def __setitem__(self, key, val):
        #cdef str msg
        #cdef object retrieved
        #cdef ConfigData conf
        #cdef object main = self.__main
        #cdef object base = self.__base
        main = self.__main
        base = self.__base
        # check the key validity
        if not isinstance(key, (str,bytes)):
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

#cdef class Config:
class Config(object):
    '''Configuration maintenance class'''

    #def __cinit__(self, _base = None, **args):
    def __init__(self, _base = None, **args):
        #self.data = ConfigData(_base)
        self.data = ConfigData(_base=_base)
        self.base = self.data.__base
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

    #def load_json(self, str str_json, bool override=True):
    def load_json(self, str_json, override=True):
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

    @cython.locals(dtype = type)
    @cython.locals(data = ConfigData)
    @cython.locals(dic = object)
    def to_dict(self, key=None, ordered=False, upstream=False, recursive=True, purge=False, flat=False):
        #cdef type dtype
        #cdef ConfigData data = self.data
        data = self.data
        #cdef object dic
        #cdef object dic
        if ordered:
            dtype = OrderedDict
        else:
            dtype = dict
        if key:
            data = data[key]
        dic = data2dict(data, dtype, upstream, recursive, purge)
        if flat:
            #return flat_dict(data2dict(data, dtype, upstream, recursive), dtype, False)
            #return flat_dict(data2dict(data, dtype, upstream, recursive, purge), dtype, False)
            return flat_dict(dic, dtype, False)
        else:
            #return data2dict(data, dtype, upstream, recursive)
            #return data2dict(data, dtype, upstream, recursive, purge)
            return dic

    @cython.locals(d = object)
    def to_json(self, key=None, upstream=False, purge=None, **options):
        #cdef object d
        d = self.to_dict(key, True, upstream, True, purge, False)
        return json.dumps(d, **options)

    def update(self, _conf = None, _override=True, _override_none=False, **args):
        #if _conf:
        #    if _override:
        #        for key, val in _conf.items():
        #            if val != None:
        #                #dprint(key)
        #                #dprint(val)
        #                self[key] = val
        #    else:
        #        for key in _conf:
        #            if key not in self:
        #                self[key] = _conf[key]
        #if args:
        #    self.update(args, _override)
        #update_data(self.data, _conf, _override, **args)
        update_data(self.data, _conf, _override, _override_none, **args)
        return self

    def __contains__(self, key):
        return self.data.__contains__(key)

    def __getitem__(self, key):
        return self.data.__getitem__(key)

    def __iter__(self):
        return self.data.__iter__()

    def __len__(self):
        return self.data.__len__()

    @cython.locals(cls = type)
    @cython.locals(name = str)
    def __repr__(self):
        #cdef type cls
        #cdef str name
        cls = self.__class__
        name = cls.__name__
        #strParams = get_key_val_str(vars(self.data), False)
        return "%s(%r)" % (name, self.data)

    def __setitem__(self, key, val):
        self.data.__setitem__(key, val)

#def get_items(object data, bool purge):
def get_items(data, purge):
    for key in data:
        val = data[key]
        if should_take(val, purge):
            yield key, val

#cdef bool should_take(object val, bool purge):
def should_take(val, purge):
    if not purge:
        return True
    if val is None:
        return False
    elif isinstance(val, ConfigData):
        if len(val) == 0:
            return False
    elif isinstance(val, dict):
        if len(val) == 0:
            return False
    return True

# type object is problematic in python 3.6?
#cdef object data2dict(object data, type dtype, bool upstream, bool recursive):
#cdef object data2dict(object data, object dtype, bool upstream, bool recursive):
#cdef object data2dict(object data, object dtype, bool upstream, bool recursive, bool purge):
@cython.locals(cdata = ConfigData)
@cython.locals(items = object)
def data2dict(data, dtype, upstream, recursive, purge):
    #dprint("--")
    #dprint(data)
    #dprint(dtype)
    #dprint(upstream)
    #dprint(recursive)
    #cdef ConfigData cdata
    #cdef object items
    #data = data
    if not isinstance(data, ConfigData):
        # as-is
        return data
    cdata = data
    if not recursive:
        if upstream:
            #return dtype((key,data[key]) for key in data)
            #return dtype(get_items(data))
            items = get_items(cdata, purge)
        else:
            #return dtype((key,data[key]) for key in cdata.__main)
            items = get_items(cdata.__main, purge)
        return dtype(items)
    else:
        if upstream:
            #return dtype((key,data2dict(data[key],dtype,upstream,recursive)) for key in data)
            #return dtype((key,data2dict(data[key], dtype, upstream, recursive, purge)) for key in data)
            #return dtype((key,data2dict(val, dtype, upstream, recursive, purge)) for key, val in get_items(cdata, purge))
            #items = ((key, data2dict(val, dtype, upstream, recursive, purge)) for key, val in cdata)
            pass
        else:
            #dprint(cdata.__main)
            #return dtype((key,data2dict(data[key],dtype,upstream,recursive)) for key in cdata.__main)
            #return dtype((key,data2dict(data[key], dtype, upstream, recursive, purge)) for key in cdata.__main)
            #return dtype((key,data2dict(val, dtype, upstream, recursive, purge)) for key, val in get_items(cdata.__main, purge))
            data = cdata.__main
        #items = ((key,data2dict(val, dtype, upstream, recursive, purge)) for key, val in get_items(data, purge))
        items = [(key,data2dict(val, dtype, upstream, recursive, purge)) for key, val in get_items(data, purge)]
        if purge:
            #items = ((key, val) for key, val in items if should_take(val, purge))
            items = [(key, val) for key, val in items if should_take(val, purge)]
        return dtype(items)

#cdef object dict2data(object obj):
@cython.locals(key = object, value = object)
@cython.locals(conf = ConfigData)
def dict2data(obj):
    #cdef object key, value
    #cdef ConfigData conf
    if not isinstance(obj, dict):
        # as-is
        return obj
    conf = ConfigData()
    for key, value in obj.items():
        conf[key] = dict2data(value)
    return conf

#cdef get_key_val_str(object d, bool verbose):
def get_key_val_str(d, verbose):
    if verbose:
        items = ["%s=%r" % (t[0],t[1]) for t in d.items()]
    else:
        items = ["%s=%r" % (t[0],t[1]) for t in d.items() if not t[0].startswith('_')]
    return str.join(', ', items)

#cdef list flat_items(object items, str prefix, bool chain_key):
@cython.locals(flatten = list)
@cython.locals(str_prefix = str)
@cython.locals(full_key = str)
def flat_items(items, prefix, chain_key):
    #cdef object flatten = []
    #cdef str str_prefix
    #cdef str full_key
    flatten = []
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
#cdef object flat_dict(object d, type dtype, bool chain_key):
@cython.locals(flatten = object)
def flat_dict(d, dtype, chain_key):
    #cdef object flatten = dtype()
    flatten = dtype()
    for key, val in flat_items(d.items(), None, chain_key):
        if key not in flatten:
            flatten[key] = val
    return flatten

#def update_data(ConfigData cdata, _conf = None, _override=True, **args):
#def update_data(ConfigData cdata, _conf = None, _override=True, _override_none=False, **args):
def update_data(cdata, _conf = None, _override=True, _override_none=False, **args):
    cdata = update_data(cdata, _conf, _override, _override_none)
    if args:
        cdata = update_data(cdata, args, _override, _override_none)
    return cdata
#def update_data(cdata, _conf = None, _override=True, _override_none=False, **args):
def _update_data(cdata, _conf = None, _override=True, _override_none=False):
    #if _conf:
    if isinstance(_conf, (dict,ConfigData)):
        if isinstance(_conf, ConfigData):
            _conf = ConfigData.__main
        if _override:
            for key, val in _conf.items():
                if val is None:
                    if _override_none:
                        cdata[key] = None
                else:
                    if isinstance(val, (dict,ConfigData)):
                        if key not in cdata:
                            cdata[key] = {}
                        elif not isinstance(cdata[key], ConfigData):
                            cdata[key] = {}
                        else:
                            # cdata[key] is instance of ConfigData
                            pass
                        update_data(cdata[key], val)
                    else:
                        cdata[key] = val
        else:
            for key in _conf:
                if key not in cdata:
                    cdata[key] = _conf[key]
    else:
        raise TypeError("unsupported configuration type: {}".type(_conf).__name__)
    return cdata
