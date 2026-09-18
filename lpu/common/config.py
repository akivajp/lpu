# cython: profile=True

'''Configuration utility class for function settings'''

from __future__ import annotations

# Standard libraries
import json
from collections import OrderedDict
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

# Local libraries
from lpu.common import logging
logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

class ConfigData:
    '''Configuration data holder'''

    # The actual storage is written into __dict__ under mangled aliases in
    # __init__ (see the comment there). These declarations only let the type
    # checker see the attributes.
    # (実体は __init__ 内で __dict__ に名前修飾付きの別名として書き込まれる。
    #  ここでの宣言は型チェッカーが属性を認識するためのもの)
    __base: OrderedDict[str, Any] | ConfigData | None
    __main: OrderedDict[str, Any]

    def __init__(self, _base: Any = None, **args: Any) -> None:
        base: OrderedDict[str, Any] | ConfigData | None = None
        main: OrderedDict[str, Any]
        if isinstance(_base, Config):
            base = _base.data
        elif isinstance(_base, ConfigData):
            base = _base
        elif isinstance(_base, dict):
            base = dict2data(_base)
        main = OrderedDict()
        # __setattr__ is overridden, so write into __dict__ directly.
        # The same value is registered under several aliases to absorb the
        # differences in name mangling between the referring classes.
        # __setattr__ をオーバーライドしているため、__dict__ に直接書き込む。
        # 名前修飾 (name mangling) の違いを吸収するため、参照元のクラスごとに
        # 別名でも登録しておく
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

    def __contains__(self, key: Any) -> bool:
        main = self.__main
        base = self.__base
        if isinstance(key, str) and key.find('.') >= 0:
            # chained key access
            try:
                first_key, remain_keys = key.split('.', 1)
                return self.__getitem__(first_key).__contains__(remain_keys)
            except Exception:
                return False
        elif main.__contains__(key):
            return True
        elif base and base.__contains__(key):
            return True
        return False

    def __delattr__(self, key: str) -> None:
        if key in self.__main:
            del self.__main[key]
        else:
            name = self.__class__.__name__
            raise AttributeError(f"'{name}' object has no attribute '{key}'")

    def __getattr__(self, key: str) -> Any:
        try:
            return self.__getitem__(key)
        except Exception:
            name = self.__class__.__name__
            dprint(name)
            dprint(key)
            # 元の例外 (KeyError 等) はデバッグ目的で既に記録済みのため、
            # チェーンを抑制して通常の AttributeError として見せる
            raise AttributeError(f"'{name}' object has no attribute '{key}'") from None

    def __getitem__(self, key: Any) -> Any:
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

    def __iter__(self) -> Iterator[str]:
        base = self.__base
        main = self.__main
        l = []
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

    def __len__(self) -> int:
        #return len(set(self))
        return sum(1 for _ in self)

    def __repr__(self) -> str:
        name = self.__class__.__name__
        main = self.__main
        base = self.__base
        #    str_base = repr(base)
        #    str_base = ""
        str_params = get_key_val_str(main, False)
        if base:
            if str_params:
                return f"{name}({base!r},{str_params})"
            else:
                return f"{name}({base!r})"
        else:
            if str_params:
                return f"{name}({str_params})"
            else:
                return f"{name}()"
        #    return "%s(%r, %s)" % (name,self.__base,str_params)
        #    return "%s(%s)" % (name,self.__base)

    def __setattr__(self, key: str, val: Any) -> None:
        self.__setitem__(key, val)
        #if key.startswith('_'):
        #    raise KeyError('Key should not start with "_": %s' % key)
        #    #self.__dict__.__setitem__(key, val)
        #    self.__main.__setitem__(key, val)

    ##@cython.locals(conf = ConfigData) # error in python 3.x
    def __setitem__(self, key: str, val: Any) -> None:
        main = self.__main
        base = self.__base
        # check the key validity
        if not isinstance(key, (str,bytes)):
            raise TypeError(f'key value should be type of str, but given: {type(key).__name__}')
        elif key.startswith('_'):
            raise KeyError(f'key should not start with "_": {key}')
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
                # use the narrowed local alias (base) rather than re-reading
                # self.__base, whose Optional type the checker cannot narrow
                # (真偽判定済みのローカル変数 base を使う。self.__base を
                #  再読み込みすると None 含みの型のままで絞り込めないため)
                retrieved = base.__getitem__(first_key)
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

class Config:
    '''Configuration maintenance class'''

    #def __cinit__(self, _base = None, **args):
    def __init__(self, _base: Any = None, **args: Any) -> None:
        #self.data = ConfigData(_base)
        self.data = ConfigData(_base=_base)
        self.base = self.data.__base
        if args:
            self.update(args)

    def cast(self, name: str, typeof: type) -> Any:
        val = self.require_any(name)
        if type(val) == typeof:
            return val
        else:
            casted = typeof(val)
            #self.data.__dict__[name] = newVal
            self.data[name] = casted
            return casted

    def has(self, key: str | Iterable[str]) -> bool:
        if type(key) is str:
            return key in self
        elif isinstance(key, Iterable):
            return all(map(self.has, key))
        else:
            raise TypeError(f"Expected str or iterable type, but given: {type(key).__name__}")

    def get(self, key: str | Iterable[str], default: Any = None) -> Any:
        if type(key) is str:
            if key in self:
                return self[key]
            else:
                return default
        elif isinstance(key, Iterable):
            return [self.get(elem, default) for elem in key]
        else:
            raise TypeError(f"Expected str or iterable type, but given: {type(key).__name__}")

    def items(self) -> Iterator[tuple[str, Any]]:
        for key in self:
            yield key, self[key]

    #def load_json(self, str str_json, bool override=True):
    def load_json(self, str_json: str | bytes, override: bool = True) -> Config:
        #self.update(json.loads(compat.to_str(strJSON)))
        #uniDict = json.loads(strJSON)
        d = json.loads(str_json, object_pairs_hook=OrderedDict)
        d = flat_dict(d, OrderedDict, True)
        #self.update(compat.to_str(uniDict))
        self.update(d, override)
        return self

    def require(
        self,
        name: str,
        desc: str | None = None,
        typeOf: type | None = None,
    ) -> Any:
        val = self.require_any(name, desc)
        if typeOf:
            self.require_type(name, typeOf)
        return val

    def require_any(self, name: str, desc: str | None = None) -> Any:
        if name not in self.data:
            if desc:
                raise KeyError(f'Configuration "{name}" ({desc}) is not defined')
            else:
                raise KeyError(f'Configuration "{name}" is not defined')
        return self.data.__getitem__(name)

    def require_type(self, name: str, typeOf: type) -> Any:
        val = self.require_any(name)
        if type(val) != typeOf:
            msg = 'Configuration "%s" should be type of %s, but given %s'
            # lpu.common.logging has no alert(); the original call would have
            # crashed with AttributeError instead of reporting the mismatch.
            # (lpu.common.logging には alert() が存在せず、元の呼び出しは
            #  型不一致の報告ではなく AttributeError で落ちていた)
            logger.error(msg % (name, typeOf, type(val)))
        return val

    def set(self, key: str, val: Any) -> Any:
        self[key] = val
        return self[key]

    def setdefault(self, key: str, val: Any) -> Any:
        if key not in self:
            return self.set(key, val)
        elif self[key] == None:
            return self.set(key, val)
        else:
            return self[key]

    def to_dict(
        self,
        key: str | None = None,
        ordered: bool = False,
        upstream: bool = False,
        recursive: bool = True,
        purge: bool | None = False,
        flat: bool = False,
    ) -> dict[str, Any]:
        data = self.data
        dtype: type
        if ordered:
            dtype = OrderedDict
        else:
            dtype = dict
        if key:
            data = data[key]
        # purge is only used truthily, so a None purge is normalized to False
        # (purge は真偽値としてのみ使われるため、None は False に正規化する)
        dic = data2dict(data, dtype, upstream, recursive, bool(purge))
        if flat:
            #return flat_dict(data2dict(data, dtype, upstream, recursive), dtype, False)
            #return flat_dict(data2dict(data, dtype, upstream, recursive, purge), dtype, False)
            return flat_dict(dic, dtype, False)
        else:
            #return data2dict(data, dtype, upstream, recursive)
            #return data2dict(data, dtype, upstream, recursive, purge)
            return dic

    #def to_json(self, key=None, upstream=False, purge=None, **options):
    def to_json(
        self,
        key: str | None = None,
        upstream: bool = True,
        purge: bool | None = None,
        **options: Any,
    ) -> str:
        # purge is only used truthily, so a None purge is normalized to False
        # (purge は真偽値としてのみ使われるため、None は False に正規化する)
        d = self.to_dict(key, True, upstream, True, bool(purge), False)
        return json.dumps(d, **options)

    def update(
        self,
        _conf: Any = None,
        _override: bool = True,
        _override_none: bool = False,
        **args: Any,
    ) -> Config:
        #if _conf:
        #            if val != None:
        #                #dprint(key)
        #                #dprint(val)
        #                self[key] = _conf[key]
        #    self.update(args, _override)
        #update_data(self.data, _conf, _override, **args)
        update_data(self.data, _conf, _override, _override_none, **args)
        return self

    def __contains__(self, key: Any) -> bool:
        return self.data.__contains__(key)

    def __getitem__(self, key: Any) -> Any:
        return self.data.__getitem__(key)

    def __iter__(self) -> Iterator[str]:
        return self.data.__iter__()

    def __len__(self) -> int:
        return self.data.__len__()

    def __repr__(self) -> str:
        cls = self.__class__
        name = cls.__name__
        #strParams = get_key_val_str(vars(self.data), False)
        return f"{name}({self.data!r})"

    def __setitem__(self, key: str, val: Any) -> None:
        self.data.__setitem__(key, val)

#def get_items(object data, bool purge):
def get_items(data: Any, purge: bool) -> Iterator[tuple[str, Any]]:
    for key in data:
        val = data[key]
        if should_take(val, purge):
            yield key, val

def should_take(val: Any, purge: bool) -> bool:
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
def data2dict(
    data: Any,
    dtype: type,
    upstream: bool,
    recursive: bool,
    purge: bool,
) -> Any:
    #data = data
    if not isinstance(data, ConfigData):
        # as-is
        return data
    cdata = data
    if not recursive:
        if upstream:
            #return dtype((key,data[key]) for key in data)
            #return dtype(get_items(data))
            items: Iterable[tuple[str, Any]] = get_items(cdata, purge)
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
            #return dtype((key,data2dict(data[key],dtype,upstream,recursive)) for key in cdata.__main)
            #return dtype((key,data2dict(data[key], dtype, upstream, recursive, purge)) for key in cdata.__main)
            #return dtype((key,data2dict(val, dtype, upstream, recursive, purge)) for key, val in get_items(cdata.__main, purge))
            data = cdata.__main
        #items = ((key,data2dict(val, dtype, upstream, recursive, purge)) for key, val in get_items(data, purge))
        items = [
            (key, data2dict(val, dtype, upstream, recursive, purge))
            for key, val in get_items(data, purge)
        ]
        if purge:
            #items = ((key, val) for key, val in items if should_take(val, purge))
            items = [(key, val) for key, val in items if should_take(val, purge)]
        return dtype(items)

def dict2data(obj: Any) -> Any:
    if not isinstance(obj, dict):
        # as-is
        return obj
    conf = ConfigData()
    for key, value in obj.items():
        conf[key] = dict2data(value)
    return conf

def get_key_val_str(d: Mapping[str, Any], verbose: bool) -> str:
    if verbose:
        items = [f"{t[0]}={t[1]!r}" for t in d.items()]
    else:
        items = [f"{t[0]}={t[1]!r}" for t in d.items() if not t[0].startswith('_')]
    return str.join(', ', items)

def flat_items(
    items: Iterable[tuple[str, Any]],
    prefix: str | None,
    chain_key: bool,
) -> list[tuple[str, Any]]:
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
def flat_dict(
    d: Mapping[str, Any],
    dtype: type,
    chain_key: bool,
) -> dict[str, Any]:
    flatten = dtype()
    for key, val in flat_items(d.items(), None, chain_key):
        if key not in flatten:
            flatten[key] = val
    return flatten

def update_data(
    cdata: Any,
    _conf: Any = None,
    _override: bool = True,
    _override_none: bool = False,
    **args: Any,
) -> Any:
    cdata = _update_data(cdata, _conf, _override, _override_none)
    if args:
        cdata = _update_data(cdata, args, _override, _override_none)
    return cdata
def _update_data(
    cdata: Any,
    _conf: Any = None,
    _override: bool = True,
    _override_none: bool = False,
) -> Any:
    if _conf is None:
        # Nothing to do when no source is given. This branch is taken when
        # called with keyword arguments only, as in Config.update(key=value).
        # 更新元が指定されていない場合は何もしない
        # (Config.update(key=value) のようにキーワード引数のみで
        #  呼び出された場合にここを通る)
        return cdata
    if isinstance(_conf, (dict,ConfigData)):
        if isinstance(_conf, ConfigData):
            # ConfigData has no items(), and its values are split between the
            # base (inherited) and the main (overriding) layer. Iterating the
            # object itself yields the merged view of the two, so build a
            # plain dict from that.
            # 0.2.x referred to ConfigData.__main as a class attribute here,
            # which always failed.
            # ConfigData は items() を持たず、値は base (継承層) と
            # main (上書き層) に分かれて保持される。オブジェクト自身を反復
            # すると両者をマージした一覧が得られるため、そこから辞書を作る。
            # 0.2.x ではここで ConfigData.__main をクラス属性として参照して
            # いたため、常に失敗していた。
            _conf = {key: _conf[key] for key in _conf}
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
        raise TypeError(f"unsupported configuration type: {type(_conf).__name__}")
    return cdata
