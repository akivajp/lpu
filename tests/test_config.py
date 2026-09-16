# -*- coding: utf-8 -*-

'''Tests for lpu.common.config

lpu.common.config のテスト。
'''

import json

import pytest

from lpu.common.config import Config
from lpu.common.config import ConfigData


class TestBasicAccess:
    '''Attribute and item access / 属性アクセスと添字アクセス'''

    def test_init_from_dict(self):
        conf = Config({'a': 1, 'b': 'x'})
        assert conf.data.a == 1
        assert conf['b'] == 'x'

    def test_set_by_attribute_and_item(self):
        conf = Config()
        conf.data.a = 1
        conf['b'] = 2
        assert conf.data.a == 1
        assert conf.data.b == 2

    def test_nested_dict_becomes_config_data(self):
        conf = Config({'nested': {'x': 10}})
        assert isinstance(conf.data.nested, ConfigData)
        assert conf.data.nested.x == 10

    def test_chained_key_access(self):
        conf = Config({'nested': {'x': 10}})
        assert conf['nested.x'] == 10

    def test_contains_and_len(self):
        conf = Config({'a': 1, 'b': 2})
        assert 'a' in conf
        assert 'z' not in conf
        assert len(conf) == 2

    def test_get_with_default(self):
        conf = Config({'a': 1})
        assert conf.get('a') == 1
        assert conf.get('z', 'fallback') == 'fallback'


class TestUpdate:
    '''Regression tests for Config.update / Config.update の回帰テスト'''

    def test_update_with_keyword_arguments_only(self):
        '''Keyword-only update must not raise

        Up to 0.2.x this always raised, because _update_data rejected
        _conf=None. It made lpu-word-align-train unusable.

        キーワード引数のみの update が例外を投げないこと。
        0.2.x までは _update_data が _conf=None を拒否したため必ず失敗し、
        lpu-word-align-train が利用できなかった。
        '''
        conf = Config({'a': 1})
        conf.update(b=2)
        assert conf.data.a == 1
        assert conf.data.b == 2

    def test_update_with_no_arguments_is_a_noop(self):
        conf = Config({'a': 1})
        conf.update()
        assert conf.data.a == 1

    def test_update_from_dict(self):
        conf = Config({'a': 1})
        conf.update({'a': 9, 'b': 2})
        assert conf.data.a == 9
        assert conf.data.b == 2

    def test_update_from_config_data(self):
        '''Updating from a ConfigData instance must work

        0.2.x looked up ConfigData.__main as a class attribute, which failed.

        ConfigData インスタンスからの更新が動作すること。
        0.2.x では ConfigData.__main をクラス属性として参照していて失敗した。
        '''
        source = Config({'a': 9, 'b': 2})
        conf = Config({'a': 1})
        conf.update(source.data)
        assert conf.data.a == 9
        assert conf.data.b == 2

    def test_update_without_override_keeps_existing(self):
        conf = Config({'a': 1})
        conf.update({'a': 9, 'b': 2}, False)
        assert conf.data.a == 1
        assert conf.data.b == 2

    def test_update_rejects_unsupported_type(self):
        '''An unsupported type raises TypeError, not AttributeError

        0.2.x had a missing .format() call in the error message, so the
        raise statement itself failed with AttributeError.

        非対応の型では TypeError が上がること。
        0.2.x はエラーメッセージの .format() 呼び出しが漏れており、
        raise 文自体が AttributeError で失敗していた。
        '''
        conf = Config()
        with pytest.raises(TypeError):
            conf.update('not a mapping')


class TestSerialization:
    def test_to_dict_needs_upstream_for_inherited_values(self):
        '''A dict given positionally becomes the inherited (base) layer

        Config(mapping) puts the mapping into the base layer, so to_dict()
        needs upstream=True to see it, while to_json() defaults to True.

        位置引数で渡した辞書は継承層 (base) に入る。
        そのため to_dict() では upstream=True が必要で、
        to_json() は既定で True になっている。
        '''
        conf = Config({'a': 1, 'nested': {'x': 10}})
        assert conf.to_dict() == {}
        assert conf.to_dict(upstream=True) == {'a': 1, 'nested': {'x': 10}}
        assert json.loads(conf.to_json()) == {'a': 1, 'nested': {'x': 10}}

    def test_to_dict_returns_values_set_on_the_main_layer(self):
        conf = Config()
        conf.data.a = 1
        assert conf.to_dict() == {'a': 1}

    def test_load_json(self):
        conf = Config()
        conf.load_json('{"a": 1}')
        assert conf.data.a == 1

    def test_inheritance_from_base_config(self):
        '''Values of the base config are visible through the derived one

        派生側から基底 Config の値が参照できること。
        '''
        base = Config({'a': 1})
        derived = Config(base)
        assert derived.data.a == 1
        derived.data.a = 2
        # The base must not be modified / 基底側は変更されないこと
        assert base.data.a == 1
        assert derived.data.a == 2


class TestRequire:
    def test_require_passes_for_existing_key(self):
        conf = Config({'a': 1})
        assert conf.require('a')

    def test_require_raises_for_missing_key(self):
        conf = Config()
        with pytest.raises(Exception):
            conf.require('missing')
