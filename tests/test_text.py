# -*- coding: utf-8 -*-

'''Tests for lpu.common.text and the deprecated lpu.common.compat alias

lpu.common.text と、非推奨エイリアス lpu.common.compat のテスト。
'''

import warnings

import pytest

from lpu.common import text


class TestToStr:
    '''to_str tolerates decode failures / to_str はデコード失敗を許容する'''

    def test_passes_str_through(self):
        assert text.to_str('abc') == 'abc'

    def test_decodes_utf8_bytes(self):
        assert text.to_str('あ'.encode('utf-8')) == 'あ'

    def test_escapes_invalid_bytes_instead_of_raising(self):
        # Invalid UTF-8 must not raise / 不正な UTF-8 で例外を投げないこと
        assert text.to_str(b'\xff') == '\\xff'

    def test_converts_other_objects(self):
        assert text.to_str(123) == '123'


class TestToUnicode:
    '''to_unicode is strict / to_unicode は厳密にデコードする'''

    def test_decodes_utf8_bytes(self):
        assert text.to_unicode('あ'.encode('utf-8')) == 'あ'

    def test_raises_on_invalid_bytes(self):
        with pytest.raises(UnicodeDecodeError):
            text.to_unicode(b'\xff')

    def test_converts_other_objects(self):
        assert text.to_unicode(123) == '123'


class TestToBytes:
    def test_encodes_str_as_utf8(self):
        assert text.to_bytes('あ') == 'あ'.encode('utf-8')

    def test_passes_bytes_through(self):
        assert text.to_bytes(b'abc') == b'abc'

    def test_converts_other_objects(self):
        assert text.to_bytes(123) == b'123'


def test_compat_module_is_deprecated_but_still_works():
    '''lpu.common.compat warns on import and keeps delegating

    lpu.common.compat は import 時に警告を出しつつ委譲を続ける。
    '''
    import sys
    sys.modules.pop('lpu.common.compat', None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        from lpu.common import compat
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    assert compat.to_str(b'abc') == 'abc'
    assert compat.to_bytes('abc') == b'abc'
    assert compat.reduce(lambda a, b: a + b, [1, 2, 3]) == 6
    assert list(compat.zip([1, 2], 'ab')) == [(1, 'a'), (2, 'b')]
