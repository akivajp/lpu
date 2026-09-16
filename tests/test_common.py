# -*- coding: utf-8 -*-

'''Tests for the remaining lpu.common modules

lpu.common の残りのモジュールのテスト。
'''

import gzip
import io
import os

import pytest

from lpu.common import colors
from lpu.common import environ
from lpu.common import logging
from lpu.common import numbers
from lpu.common import progress
from lpu.common import validation
from lpu.common import vocab


class TestNumbers:
    @pytest.mark.parametrize('value,margin,expected', [
        (3.0, 0, 3),
        (3.5, 0, 3.5),
        (3.0000001, 1e-5, 3),
        (3.01, 1e-5, 3.01),
        ('42', 0, 42),
    ])
    def test_to_number(self, value, margin, expected):
        result = numbers.toNumber(value, margin)
        assert result == expected
        assert isinstance(result, type(expected))

    @pytest.mark.parametrize('value,length', [(0, 1), (255, 1), (65535, 2),
                                              (1, 4)])
    def test_int_bytes_round_trip(self, value, length):
        encoded = numbers.intToBytes(value, length)
        assert len(encoded) == length
        assert numbers.intFromBytes(encoded) == value

    def test_byteorder_is_respected(self):
        assert numbers.intToBytes(1, 2, 'big') == b'\x00\x01'
        assert numbers.intToBytes(1, 2, 'little') == b'\x01\x00'


class TestEnviron:
    def test_get_env_falls_back_to_the_default(self):
        assert environ.get_env('LPU_TEST_UNSET_VAR', 'fallback') == 'fallback'

    def test_push_restores_the_previous_value(self, monkeypatch):
        '''Leaving the stack layer must restore the environment

        Only variables assigned through set() are tracked; a raw
        os.environ assignment is deliberately left untouched.

        スタック層を抜けると環境変数が復元されること。
        追跡されるのは set() 経由で設定した変数のみで、os.environ への
        直接代入は意図的に対象外である。
        '''
        monkeypatch.setenv('LPU_TEST_VAR', 'base')
        with environ.push() as holder:
            holder.set('LPU_TEST_VAR', 'pushed')
            assert os.environ['LPU_TEST_VAR'] == 'pushed'
        assert os.environ['LPU_TEST_VAR'] == 'base'

    def test_push_can_set_values_directly(self, monkeypatch):
        monkeypatch.delenv('LPU_TEST_VAR', raising=False)
        with environ.push(LPU_TEST_VAR='value'):
            assert os.environ['LPU_TEST_VAR'] == 'value'
        assert 'LPU_TEST_VAR' not in os.environ

    def test_nested_layers_unwind_in_order(self, monkeypatch):
        monkeypatch.setenv('LPU_TEST_VAR', 'base')
        with environ.push() as outer:
            outer.set('LPU_TEST_VAR', 'outer')
            with environ.push() as inner:
                inner.set('LPU_TEST_VAR', 'inner')
                assert os.environ['LPU_TEST_VAR'] == 'inner'
                assert environ.get_env('LPU_TEST_VAR') == 'inner'
            assert os.environ['LPU_TEST_VAR'] == 'outer'
            assert environ.get_env('LPU_TEST_VAR') == 'outer'
        assert os.environ['LPU_TEST_VAR'] == 'base'

    def test_unset_restores_one_key_without_dropping_the_others(self,
                                                                monkeypatch):
        '''unset() must affect only the given key

        Up to 0.2.x unset() also discarded the records of every other
        variable in the layer, so they were never restored afterwards.

        unset() が指定したキーのみに作用すること。
        0.2.x までは層内の他の変数の記録も破棄していたため、以降それらが
        復元されなくなっていた。
        '''
        monkeypatch.setenv('LPU_TEST_A', 'base_a')
        monkeypatch.setenv('LPU_TEST_B', 'base_b')
        with environ.push() as holder:
            holder.set('LPU_TEST_A', 'new_a')
            holder.set('LPU_TEST_B', 'new_b')
            holder.unset('LPU_TEST_A')
            assert os.environ['LPU_TEST_A'] == 'base_a'
            assert os.environ['LPU_TEST_B'] == 'new_b'
        assert os.environ['LPU_TEST_B'] == 'base_b'

    def test_the_shared_stack_does_not_grow(self):
        '''Each layer is dropped from the shared stack on exit

        Up to 0.2.x env_stack grew monotonically.

        層は終了時に共有スタックから取り除かれること。
        0.2.x までは env_stack が単調に増え続けていた。
        '''
        depth = len(environ.env_stack)
        for _ in range(5):
            with environ.push():
                pass
        assert len(environ.env_stack) == depth


class TestColors:
    def test_put_color_wraps_the_text_in_escape_sequences(self):
        colored = colors.put_color('text', 'red')
        assert 'text' in colored
        assert colored != 'text'
        assert '\033[' in colored


class TestValidation:
    def test_type_names_string_for_a_single_type(self):
        assert validation.to_type_names_string(str) == 'str'

    def test_type_names_string_joins_multiple_types(self):
        assert validation.to_type_names_string([str, int]) == 'str or int'
        assert (validation.to_type_names_string([str, int, float])
                == 'str, int or float')

    def test_check_argument_type_accepts_a_valid_value(self):
        assert validation.check_argument_type('x', 'name', str)

    def test_check_argument_type_rejects_an_invalid_value(self):
        with pytest.raises(TypeError):
            validation.check_argument_type(1, 'name', str)


class TestLogging:
    def test_get_color_logger_returns_a_custom_logger(self):
        logger = logging.getColorLogger('lpu.test.logger')
        assert hasattr(logger, 'debug_print')

    def test_using_config_toggles_the_debug_level(self):
        '''The context manager enables debug only inside the block

        On exit the logger is reconfigured from the restored environment
        variables, which puts it back to the normal verbose level.

        コンテキストマネージャがブロック内でのみ debug を有効にすること。
        終了時は復元された環境変数からロガーが再設定され、通常の
        verbose レベルに戻る。
        '''
        name = 'lpu.test.using_config'
        logger = logging.getColorLogger(name)
        with logging.using_config(name, debug=True):
            assert logger.level == logging.DEBUG
        assert logger.level != logging.DEBUG
        assert logger.level == logging.INFO

    def test_using_config_enables_quiet_mode(self):
        name = 'lpu.test.using_config_quiet'
        logger = logging.getColorLogger(name)
        with logging.using_config(name, quiet=True):
            assert logger.level == logging.ERROR
        assert logger.level == logging.INFO

    def test_level_string(self):
        assert logging.getLevelString(logging.DEBUG) == 'DEBUG'
        assert logging.getLevelString(logging.ERROR) == 'ERROR'

    def test_debug_print_reports_the_expression_source(self, caplog):
        '''debug_print logs the source expression next to its value

        This is the distinctive feature of the module: the caller's source
        line is parsed to recover the name of the printed expression.

        debug_print が値とともに元の式を出力すること。
        呼び出し元のソース行を解析して式名を復元するのが本モジュールの特徴。
        '''
        logger = logging.getColorLogger('lpu.test.debug_print')
        with caplog.at_level(logging.DEBUG, logger='lpu.test.debug_print'):
            with logging.using_config('lpu.test.debug_print', debug=True):
                some_variable = 12345
                logger.debug_print(some_variable)
        assert 'some_variable' in caplog.text
        assert '12345' in caplog.text


class TestProgress:
    def test_format_time(self):
        assert progress.format_time(0) == '00:00:00'
        assert progress.format_time(61) == '00:01:01'
        assert progress.format_time(3661) == '01:01:01'

    def test_about_abbreviates_large_numbers(self):
        assert progress.about(999) == '999.000'
        assert progress.about(1500) == '1.500k'
        assert progress.about(1500000) == '1.500M'
        assert progress.about(1500000000) == '1.500G'

    def test_about_uses_binary_units_for_bytes(self):
        assert progress.about(1536, show_bytes=True) == '1.500KiB'
        assert progress.about(1536 * 1024, show_bytes=True) == '1.500MiB'

    def test_speed_counter_counts_up(self):
        counter = progress.SpeedCounter(header='test', force=False)
        for _ in range(10):
            counter.add()
        assert counter.count == 10
        counter.reset()

    def test_speed_counter_as_a_context_manager(self):
        with progress.SpeedCounter(header='test') as counter:
            counter.add(5)
            assert counter.count == 5

    def test_view_over_an_iterator_yields_every_element(self):
        source = list(range(100))
        assert list(progress.view(iter(source), header='test')) == source

    def test_view_over_a_file_yields_every_line(self, tmp_path):
        path = tmp_path / 'lines.txt'
        path.write_text('a\nb\nc\n', encoding='utf-8')
        with open(str(path)) as f:
            assert len(list(progress.view(f, header='test'))) == 3

    def test_file_reader_over_gzip_reports_progress(self, tmp_path):
        '''Reading a gzip file through FileReader must yield every line

        This is the distinctive feature of the module: progress is tracked
        by the position in the compressed stream.

        FileReader 経由で gzip を読んだとき全行が得られること。
        圧縮ストリーム上の位置で進捗を測るのが本モジュールの特徴。
        '''
        path = tmp_path / 'lines.txt.gz'
        body = ''.join('line%d\n' % i for i in range(500))
        with gzip.open(str(path), 'wt') as f:
            f.write(body)
        reader = progress.FileReader(str(path), header='test')
        try:
            assert len(list(reader)) == 500
        finally:
            reader.close()

    def test_pipe_view_hands_the_content_to_outfunc(self, tmp_path):
        '''outfunc receives the buffered content

        Up to 0.2.x outfunc was only used to suppress the stdout write and
        was never called, so the content was silently discarded.

        outfunc がバッファ内容を受け取ること。
        0.2.x までは outfunc は stdout 出力の抑止にしか使われず呼び出され
        なかったため、内容が無言で捨てられていた。
        '''
        path = tmp_path / 'lines.txt'
        path.write_text('a\nb\nc\n', encoding='utf-8')
        received = []
        progress.pipe_view([str(path)], mode='lines', header='test',
                           outfunc=received.append)
        assert b''.join(received) == b'a\nb\nc\n'


class TestVocab:
    '''StringEnumerator must not require the Cython extension

    StringEnumerator が Cython 拡張を必要としないこと。
    '''

    def test_str2id_assigns_sequential_ids(self):
        enumerator = vocab.StringEnumerator()
        assert enumerator.str2id('foo') == 0
        assert enumerator.str2id('bar') == 1
        assert enumerator.str2id('foo') == 0

    def test_id2str_inverts_str2id(self):
        enumerator = vocab.StringEnumerator()
        index = enumerator.str2id('foo')
        assert enumerator.id2str(index) == 'foo'

    def test_id2str_rejects_an_unknown_id(self):
        enumerator = vocab.StringEnumerator()
        with pytest.raises(IndexError):
            enumerator.id2str(99)

    def test_iteration_and_length(self):
        enumerator = vocab.StringEnumerator()
        for word in ['foo', 'bar']:
            enumerator.append(word)
        assert list(enumerator) == ['foo', 'bar']
        assert list(enumerator.ids()) == [0, 1]
        assert len(enumerator) == 2

    def test_word_id_conversion_helpers(self):
        index = vocab.word2id('someuniqueword')
        assert vocab.id2word(index) == 'someuniqueword'

    def test_phrase_idvec_conversion(self):
        idvec = vocab.phrase2idvec('alpha beta')
        assert vocab.idvec2phrase(idvec) == 'alpha beta'
