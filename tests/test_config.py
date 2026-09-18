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


class TestConfigDataEdges:
    '''ConfigData edge cases / ConfigData の細かい動作'''

    def test_init_with_keyword_arguments(self):
        # kwargs は main 層に入る
        data = ConfigData(a=1)
        assert data.a == 1

    def test_contains_with_chained_keys(self):
        # チェーンキーでの in 演算。失敗経路は False を返すこと
        conf = Config({'nested': {'x': 10}})
        data = conf.data
        assert 'nested.x' in data
        assert 'nested.z' not in data
        # first key resolves to a non-ConfigData value
        # (先頭キーが ConfigData 以外の場合も False)
        data.plain = 1
        assert 'plain.anything' not in data
        # first key does not exist at all
        # (先頭キー自体が存在しない場合も False)
        assert 'nowhere.anything' not in data

    def test_delattr_removes_only_existing_keys(self):
        conf = Config()
        conf.data.a = 1
        del conf.data.a
        assert 'a' not in conf.data
        with pytest.raises(AttributeError):
            del conf.data.a

    def test_getattr_raises_attribute_error_for_missing_key(self):
        conf = Config()
        with pytest.raises(AttributeError):
            conf.data.missing_key

    def test_getitem_with_missing_key_raises_key_error(self):
        data = ConfigData()
        with pytest.raises(KeyError):
            data['missing']

    def test_getitem_with_sequence_keys(self):
        # list / tuple / その他の Iterable をキーにできること
        conf = Config({'a': 1, 'b': 2})
        data = conf.data
        assert data[['a', 'b']] == [1, 2]
        assert data[('a', 'b')] == (1, 2)
        assert sorted(data[{'a', 'b'}]) == [1, 2]

    def test_getitem_with_invalid_key_type(self):
        data = ConfigData()
        with pytest.raises(TypeError):
            data[123]

    def test_setitem_rejects_invalid_keys(self):
        data = ConfigData()
        with pytest.raises(TypeError):
            data[123] = 1
        with pytest.raises(KeyError):
            data['_hidden'] = 1

    def test_repr_variants(self):
        # 空の ConfigData と、base + main を持つ ConfigData の repr
        assert repr(ConfigData()) == 'ConfigData()'
        base = ConfigData(a=1)
        derived = ConfigData(base, b=2)
        text = repr(derived)
        assert text.startswith('ConfigData(')
        assert 'b=2' in text

    def test_chained_setitem_into_main_layer(self):
        # main 層に既にある ConfigData へのチェーン代入
        conf = Config()
        conf.data['nested'] = {'x': 1}
        conf.data['nested.x'] = 2
        assert conf.data['nested.x'] == 2

    def test_chained_setitem_onto_a_plain_value_raises(self):
        # main 層の値が ConfigData 以外なら KeyError
        conf = Config()
        conf.data.plain = 1
        with pytest.raises(KeyError):
            conf.data['plain.x'] = 2

    def test_chained_setitem_derives_from_the_base_layer(self):
        # base 層に ConfigData がある場合は派生してから代入
        base = Config({'nested': {'x': 1}})
        conf = Config(base)
        conf.data['nested.x'] = 2
        assert conf.data['nested.x'] == 2
        # 基底側は変更されないこと
        assert base.data['nested.x'] == 1

    def test_chained_setitem_onto_a_base_scalar_raises(self):
        # base 層の値が ConfigData 以外なら KeyError
        base = Config({'plain': 1})
        conf = Config(base)
        with pytest.raises(KeyError):
            conf.data['plain.x'] = 2

    def test_chained_setitem_creates_new_nested_data(self):
        # 存在しないキーへのチェーン代入は新しい ConfigData を作る
        conf = Config()
        conf.data['new.x'] = 5
        assert isinstance(conf.data['new'], ConfigData)
        assert conf.data['new.x'] == 5

    def test_setitem_converts_a_dict_value(self):
        # dict を代入すると ConfigData に変換されること
        conf = Config()
        conf.data['nested'] = {'x': 1}
        assert isinstance(conf.data['nested'], ConfigData)


class TestConfigAccessors:
    '''Config helper methods / Config のヘルパーメソッド'''

    def test_init_with_keyword_arguments(self):
        conf = Config({'a': 1}, b=2)
        assert conf['a'] == 1
        assert conf['b'] == 2

    def test_cast_converts_and_stores(self):
        conf = Config()
        conf.data.num = '5'
        assert conf.cast('num', int) == 5
        assert conf.data.num == 5
        # a value with the requested type is returned as-is
        # (既に型が一致する値はそのまま返ること)
        assert conf.cast('num', int) == 5

    def test_has_accepts_an_iterable_key(self):
        conf = Config({'a': 1, 'b': 2})
        assert conf.has(['a', 'b']) is True
        assert conf.has(['a', 'missing']) is False

    def test_has_rejects_invalid_types(self):
        conf = Config()
        with pytest.raises(TypeError):
            conf.has(123)

    def test_get_with_an_iterable_key(self):
        conf = Config({'a': 1})
        assert conf.get(['a', 'missing'], 'd') == [1, 'd']
        with pytest.raises(TypeError):
            conf.get(123)

    def test_items(self):
        conf = Config()
        conf.data.a = 1
        assert list(conf.items()) == [('a', 1)]
        # iteration over the Config itself also works
        # (Config 自体の反復も動作すること)
        assert list(conf) == ['a']

    def test_repr(self):
        # dict2data wraps the given dict into a ConfigData, so the value
        # inside is nested one level deeper.
        # (dict2data が渡された辞書を ConfigData に包むため、中身は一段深く
        #  ネストされる)
        conf = Config({'a': 1})
        assert repr(conf) == 'Config(ConfigData(ConfigData(a=1)))'

    def test_require_with_a_type(self):
        conf = Config({'a': 1})
        assert conf.require('a', typeOf=int) == 1
        with pytest.raises(KeyError):
            conf.require_any('missing', 'the value')

    def test_require_type_reports_a_mismatch(self):
        # 型不一致はログに記録されつつ、値自体は返されること
        conf = Config({'a': 1})
        assert conf.require_type('a', str) == 1
        assert conf.require_type('a', int) == 1

    def test_setdefault_overrides_a_none_value(self):
        conf = Config()
        conf.data.a = None
        assert conf.setdefault('a', 5) == 5

    def test_setdefault_keeps_an_existing_value(self):
        conf = Config()
        conf.data.a = 1
        assert conf.setdefault('a', 5) == 1
        # a missing key gets set
        # (存在しないキーは設定されること)
        assert conf.setdefault('new', 7) == 7
        assert conf.data['new'] == 7

    def test_to_dict_with_a_key_and_flat(self):
        conf = Config({'nested': {'x': 10}})
        assert conf.to_dict(key='nested', upstream=True) == {'x': 10}
        # without upstream=True only the main layer is seen
        # (upstream=True 無しでは main 層のみが対象になる)
        assert conf.to_dict(key='nested') == {}
        assert conf.to_dict(key='nested', upstream=True, flat=True) == {'x': 10}


class TestDictConversion:
    '''data2dict / flat_dict / update_data edge cases
    data2dict / flat_dict / update_data の細かい動作'''

    def test_should_take(self):
        from lpu.common.config import should_take
        assert should_take(None, True) is False
        assert should_take(ConfigData(), True) is False
        assert should_take({}, True) is False
        assert should_take({'a': 1}, True) is True
        # purge=False では全て取得対象になること
        assert should_take(None, False) is True

    def test_to_dict_without_recursion(self):
        # Reading base values derives copies into the main layer
        # (copy-on-read), so each assertion uses its own instance.
        # (base 側の読み出しで main 層に派生コピーが作られるため、
        #  検証ごとに別インスタンスを用意する)
        upstream_conf = Config({'inherited': {'x': 1}})
        upstream_conf.data.local = {'y': 2}
        # Without recursion nested values stay ConfigData objects, so only
        # the key sets are compared here.
        # (非再帰ではネスト値が ConfigData のまま返るため、キー集合のみ比較)
        assert set(upstream_conf.to_dict(recursive=False, upstream=True)) == \
            {'inherited', 'local'}
        main_conf = Config({'inherited': {'x': 1}})
        main_conf.data.local = {'y': 2}
        # without upstream: only the main layer
        # (upstream 無し: main 層のみ)
        assert set(main_conf.to_dict(recursive=False)) == {'local'}

    def test_to_dict_purges_empty_values(self):
        # purge=True で None と空の辞書/ConfigData が取り除かれること
        conf = Config({'empty': {}, 'keep': 1})
        conf.data.none_value = None
        assert conf.to_dict(upstream=True, purge=True) == {'keep': 1}

    def test_get_key_val_str_verbose(self):
        from lpu.common.config import get_key_val_str
        assert get_key_val_str({'a': 1}, True) == 'a=1'

    def test_flat_dict_without_chained_keys(self):
        from lpu.common.config import flat_dict
        # chain_key=False ではネストの接頭辞が付かないこと
        assert flat_dict({'nested': {'x': 10}}, dict, True) == {'nested.x': 10}
        assert flat_dict({'nested': {'x': 10}}, dict, False) == {'x': 10}

    def test_update_with_override_none(self):
        # _override_none=True で None 値も上書きされること
        conf = Config({'a': 1})
        conf.update({'a': None}, True, True)
        assert conf['a'] is None

    def test_update_merges_nested_data(self):
        # ネストした値は既存の ConfigData にマージされること
        conf = Config()
        conf.data['nested'] = {'x': 1, 'y': 1}
        conf.update({'nested': {'x': 2, 'z': 3}})
        assert conf['nested.x'] == 2
        assert conf['nested.y'] == 1
        assert conf['nested.z'] == 3

    def test_update_creates_and_replaces_nested_data(self):
        conf = Config()
        # a missing nested key gets a fresh ConfigData
        # (無いネストキーには新しい ConfigData が作られる)
        conf.update({'fresh': {'x': 1}})
        assert conf['fresh.x'] == 1
        # a non-ConfigData value is replaced before the merge
        # (ConfigData 以外の値はマージ前に置き換えられる)
        conf.data['scalar'] = 5
        conf.update({'scalar': {'x': 2}})
        assert conf['scalar.x'] == 2
