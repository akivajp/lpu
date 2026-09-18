# -*- coding: utf-8 -*-

'''Tests for the remaining lpu.common modules

lpu.common の残りのモジュールのテスト。
'''

import gzip
import io
import logging as std_logging
import os
import sys
import types

import pytest

from lpu.common import colors
from lpu.common import dialog
from lpu.common import environ
from lpu.common import files
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

    def test_debug_print_degrades_quietly_without_source(self, caplog):
        '''Without the caller's source the value is still printed

        When there is no source to parse (stdin, a REPL, exec(), a frozen
        build) the expression cannot be recovered. 0.2.x raised a NameError
        internally and logged the whole traceback at ERROR level.

        呼び出し元のソースが無くても値は出力されること。
        解析対象のソースが無い場合 (stdin / REPL / exec() / frozen ビルド)
        は式を復元できない。0.2.x は内部で NameError を起こし、
        トレースバック全体を ERROR レベルで出力していた。
        '''
        logger = logging.getColorLogger('lpu.test.debug_print_no_source')
        namespace = {'logger': logger}
        with caplog.at_level(logging.DEBUG,
                             logger='lpu.test.debug_print_no_source'):
            with logging.using_config('lpu.test.debug_print_no_source',
                                      debug=True):
                exec('logger.debug_print(12345)', namespace)
        assert '12345' in caplog.text
        assert 'Traceback' not in caplog.text
        errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert not errors, [r.getMessage() for r in errors]

    def test_get_quiet_status_reads_the_stack(self):
        with environ.push(LPU_QUIET='1'):
            assert logging.get_quiet_status() is True
        with environ.push(LPU_QUIET='0'):
            assert logging.get_quiet_status() is False
        with environ.push(QUIET='1'):
            assert logging.get_quiet_status() is True

    def test_formatter_colorizes_by_level_format(self):
        formatter = logging.ColorizingFormatter('%(message)s')
        formatter.setLevelFormat(logging.DEBUG, 'D| %(message)s')
        formatter.setLevelColor('debug', 'green')
        record = std_logging.LogRecord('lpu.test', logging.DEBUG,
                                   'path', 1, 'hello', None, None)
        text = formatter.format(record)
        assert 'D| hello' in text

    def test_formatter_formats_exception_and_stack(self):
        import sys
        formatter = logging.ColorizingFormatter('%(message)s')
        try:
            raise ValueError('boom')
        except ValueError:
            exc_text = formatter.formatException(sys.exc_info())
        assert 'ValueError' in exc_text
        assert 'boom' in exc_text
        stack_text = formatter.formatStack('frame1\nframe2')
        assert 'frame1' in stack_text
        assert 'frame2' in stack_text

    def test_set_color_and_unset(self):
        formatter = logging.ColorizingFormatter('%(message)s')
        formatter.setColor('debug', 'green')
        assert formatter._colors['debug'] == 'green'
        formatter.setColor('DEBUG', None)
        assert 'debug' not in formatter._colors

    def test_set_colors_in_bulk(self):
        formatter = logging.ColorizingFormatter('%(message)s')
        formatter.setColors(debug='green', info='red')
        assert formatter._colors['debug'] == 'green'
        assert formatter._colors['info'] == 'red'

    def test_set_color_rejects_non_string_keywords(self):
        formatter = logging.ColorizingFormatter('%(message)s')
        with pytest.raises(TypeError):
            formatter.setColor(42, 'green')

    def test_set_color_rejects_non_string_colors(self):
        formatter = logging.ColorizingFormatter('%(message)s')
        with pytest.raises(TypeError):
            formatter.setColor('debug', 42)

    def test_filter_condition_checks_the_level(self):
        rule = logging.FilterCondition(level='DEBUG')
        debug_record = std_logging.LogRecord('lpu.test', logging.DEBUG,
                                        'path', 1, 'm', None, None)
        info_record = std_logging.LogRecord('lpu.test', logging.INFO,
                                       'path', 1, 'm', None, None)
        assert rule.filter(debug_record) is True
        assert rule.filter(info_record) is False

    def test_level_string_rejects_other_types(self):
        with pytest.raises(TypeError):
            logging.getLevelString(1.5)

    def test_config_unset_debug_and_quiet(self):
        '''set_debug / set_quiet accept False, and the unset methods clear

        LoggingConfig.set_debug / set_quiet に False を渡すとフラグが
        "0" になり、unset_debug / unset_quiet で変数自体を消せること。
        '''
        name = 'lpu.test.unset_flags'
        with logging.using_config(name, debug=True) as config:
            assert logging.get_debug_status() is True
            config.unset_debug()
            assert logging.get_debug_status() is False
            config.set_quiet(False)
            assert logging.get_quiet_status() is False
            config.set_quiet(True)
            assert logging.get_quiet_status() is True
            config.unset_quiet()
            assert logging.get_quiet_status() is False

    def test_config_without_loggers_reconfigures_the_lpu_logger(self):
        '''Without explicit loggers the global lpu logger is reconfigured

        ロガー指定が無い場合は lpu ルートロガーが再設定されること。
        '''
        with environ.push():
            config = logging.LoggingConfig()
            config.set_debug(True)
            assert logging.get_debug_status() is True

    def test_get_color_status_reads_the_env_modes(self):
        '''LPU_COLOR / COLOR select forced-on, forced-off and auto mode

        LPU_COLOR / COLOR の各指定値で on / off / auto が選択されること。
        '''
        with environ.push(LPU_COLOR='0'):
            assert logging.get_color_status() is False
        with environ.push(LPU_COLOR='off'):
            assert logging.get_color_status() is False
        with environ.push(LPU_COLOR='1'):
            assert logging.get_color_status() is True
        with environ.push(LPU_COLOR='auto'):
            # auto follows the terminal capability
            # (auto の場合はターミナルの状態に従う)
            assert logging.get_color_status() == sys.stderr.isatty()
        with environ.push(COLOR='false'):
            assert logging.get_color_status() is False
        with environ.push(LPU_COLOR='unknown-value'):
            assert logging.get_color_status() is False

    def test_formatter_uses_default_color_when_no_rule_matches(self):
        formatter = logging.ColorizingFormatter('%(message)s')
        formatter.setColor('default', 'green')
        record = std_logging.LogRecord('lpu.test', logging.INFO,
                                       'path', 1, 'hello', None, None)
        formatted = formatter.format(record)
        # the record went through put_color, so ANSI codes wrap the text
        # (put_color を通るため ANSI エスケープで囲まれる)
        assert 'hello' in formatted

    def test_formatter_colors_stack_and_exception(self):
        formatter = logging.ColorizingFormatter('%(message)s')
        formatter.setColors(stack='green', exception='red')
        assert 'frame1' in formatter.formatStack('frame1\nframe2')
        try:
            raise ValueError('boom')
        except ValueError:
            assert 'boom' in formatter.formatException(sys.exc_info())
        # without a stack / exception color, the debug / error colors are
        # used as fallbacks
        # (stack / exception 色が無い場合は debug / error 色にフォールバック)
        fallback_formatter = logging.ColorizingFormatter('%(message)s')
        fallback_formatter.setColors(debug='green', error='red')
        assert 'frame1' in fallback_formatter.formatStack('frame1\nframe2')
        try:
            raise ValueError('boom')
        except ValueError:
            assert 'boom' in fallback_formatter.formatException(
                sys.exc_info())

    def test_colorize_handler_with_explicit_mode(self):
        handler = std_logging.StreamHandler()
        formatter = logging.colorizeHandler(handler, mode='on')
        assert isinstance(formatter, logging.ColorizingFormatter)
        assert formatter._colors['debug'] == 'yellow'
        # 'off' adds the formatter without any color
        # (off では色なしのフォーマッタが設定される)
        formatter = logging.colorizeHandler(std_logging.StreamHandler(),
                                            mode='off')
        assert formatter._colors == {}
        # re-colorizing an already colorized handler is a no-op
        # (色付き済みのハンドラの再設定はそのまま返される)
        assert logging.colorizeHandler(handler, mode='auto') is handler

    def test_colorize_accepts_loggers_handlers_and_names(self):
        handler = std_logging.StreamHandler()
        logger = logging.getColorLogger('lpu.test.colorize_obj',
                                        add_handler=handler)
        assert logging.colorize(logger) is logger
        # a handler already carrying a ColorizingFormatter is returned as is
        # (既に ColorizingFormatter を持つハンドラはそのまま返される)
        assert logging.colorize(logger.handlers[0]) is logger.handlers[0]
        assert logging.colorizeLogger('lpu.test.colorize_obj') is logger

    def test_configure_logger_accepts_none_and_explicit_modes(self):
        assert logging.configureLogger(None) is None
        name = 'lpu.test.explicit_level'
        logger = logging.getColorLogger(name, level_mode=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_get_color_logger_does_not_duplicate_handlers(self):
        name = 'lpu.test.duplicate_handlers'
        handler = std_logging.StreamHandler()
        logging.getColorLogger(name, add_handler=handler)
        count = len(logging.getLogger(name).handlers)
        logging.getColorLogger(name, add_handler=handler)
        assert len(logging.getLogger(name).handlers) == count

    def test_debug_print_with_limit_and_value_types(self, caplog):
        '''debug_print handles stack limits, bytes and multi-line values

        debug_print の limit 指定と、bytes や複数行の値の出力。
        '''
        name = 'lpu.test.debug_print_types'
        logger = logging.getColorLogger(name)
        with caplog.at_level(logging.DEBUG, logger=name):
            with logging.using_config(name, debug=True):
                int_value = 42
                logger.debug_print(int_value, limit=2)
                str_value = 'plain'
                logger.debug_print(str_value)
                bytes_value = b'bytes'
                logger.debug_print(bytes_value)
                multiline_value = 'line1\nline2'
                logger.debug_print(multiline_value)
        text = caplog.text
        assert 'int_value' in text
        assert '42' in text
        assert 'str_value' in text
        assert 'plain' in text
        assert "b'bytes'" in text
        assert 'line1' in text
        assert 'line2' in text

    def test_module_level_debug_print(self, caplog):
        name = '__main__'
        with caplog.at_level(logging.DEBUG, logger=name):
            with logging.using_config(name, debug=True):
                module_value = 99
                logging.debug_print(module_value)
        assert '99' in caplog.text

    def test_seek_str_recovers_quoted_strings(self):
        assert logging._seek_str('x = "hi" there', 4)[0] == '"hi"'
        assert logging._seek_str("x = 'hi' there", 4)[0] == "'hi'"
        assert logging._seek_str('"""a b""" tail', 0)[0] == '"""a b"""'
        assert logging._seek_str("'''a b''' tail", 0)[0] == "'''a b'''"
        # an escaped character is kept inside the quoted expression
        # (エスケープ文字は式の中にそのまま保持される)
        assert logging._seek_str('x = "a\\b" tail', 4)[0] == '"a\\b"'
        # without a quote at the offset, nothing is consumed
        # (オフセット位置に引用符が無い場合は何も読まない)
        assert logging._seek_str('x = noquote', 4)[0] == ''

    def test_parse_args_recovers_argument_expressions(self):
        # nested parentheses, commas inside them and space collapsing
        # (ネストした括弧と括弧内のカンマ、スペースの連続圧縮)
        lines = ['f(1, 2 + (3),  a)\n', '  continued\n']
        feeder = logging._get_feeder(lines, 1)
        args, _ = logging._parse_args(next(feeder), feeder)
        assert args == ['1', ' 2 + (3)', ' a']
        # a nested call expression is kept as one argument
        # (ネストした呼び出し式は 1 引数として保持される)
        lines = ['f((a, b))\n']
        feeder = logging._get_feeder(lines, 1)
        args, _ = logging._parse_args(next(feeder), feeder)
        assert args == ['(a, b)']
        # a call spanning multiple lines continues on the next line
        # (複数行にまたがる呼び出しは次の行に続く)
        lines = ['log(\n', '  1)\n']
        feeder = logging._get_feeder(lines, 1)
        args, _ = logging._parse_args(next(feeder), feeder)
        # the continuation keeps the leading space
        # (継続行の先頭スペースはそのまま保持される)
        assert args == [' 1']

    def test_parse_args_rejects_unbalanced_expression(self):
        with pytest.raises(Exception, match='parse error'):
            logging._parse_args('abc)', logging._get_feeder(['x\n'], 1))

    def test_get_cached_calls_picks_the_nearest_call(self, monkeypatch):
        calls = [types.SimpleNamespace(lineno=10, col_offset=0),
                 types.SimpleNamespace(lineno=20, col_offset=0)]
        monkeypatch.setitem(logging._cached_calls, 'virtual.py', calls)
        assert logging._get_cached_calls('virtual.py', 20) is calls[1]
        # between two calls, the preceding one is used
        # (2つの呼び出しの間の行では直前のものが使われる)
        assert logging._get_cached_calls('virtual.py', 15) is calls[0]
        # before the first call, no call matches
        # (最初の呼び出しより前の行では見つからない)
        assert logging._get_cached_calls('virtual.py', 5,
                                         fallback='F') == 'F'

    def test_get_cached_calls_returns_fallback_without_source(self):
        # neither a file on disk nor a frame is available
        # (ディスク上のファイルもフレームも無い場合)
        assert logging._get_cached_calls('definitely_missing.py', 1,
                                         fallback='F') == 'F'

    def test_get_cached_line_fallbacks(self, tmp_path):
        import inspect
        frame = sys._getframe()
        # a path that does not exist falls back to the frame's source
        # (存在しないパスではフレームのソースへフォールバックする)
        src_lines = inspect.getsourcelines(frame)[0]
        line = logging._get_cached_line('definitely_missing.py', 1,
                                        fallback='F', frame=frame)
        assert line == src_lines[0]
        # an unreadable path returns the fallback
        # (読めないパスではフォールバックを返す)
        assert logging._get_cached_line(str(tmp_path), 1,
                                        fallback='G') == 'G'


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
        with gzip.open(str(path), 'wb') as f:
            f.write(body.encode('utf-8'))
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
        # Bytes, so that the comparison holds on Windows too
        # Windows でも比較が成立するようバイトで書き出す
        path.write_bytes(b'a\nb\nc\n')
        received = []
        progress.pipe_view([str(path)], mode='lines', header='test',
                           outfunc=received.append)
        assert b''.join(received) == b'a\nb\nc\n'

    def test_speed_counter_set_count_and_set_position(self):
        counter = progress.SpeedCounter(header='test')
        counter.set_count(7, view=True)
        assert counter.count == 7
        counter.set_position(7, view=True)
        assert counter.pos == 7
        counter.reset()

    def test_speed_counter_view_throttles_and_flushes(self):
        counter = progress.SpeedCounter(header='test', force=True)
        counter.set_count(5)
        assert counter.view(flush=True) is True
        # an immediate view without flush is suppressed by the interval
        # (flush 無しの直後の view はリフレッシュ間隔により抑制される)
        assert counter.view() is False
        counter.reset()

    def test_speed_counter_reset_after_activity_flushes_a_newline(
            self, capsys):
        counter = progress.SpeedCounter(header='test', force=True)
        counter.set_count(3)
        counter.view(flush=True)
        counter.reset()
        assert '\n' in capsys.readouterr().err

    def test_speed_counter_reset_accepts_new_settings(self):
        counter = progress.SpeedCounter(header='old', force=True)
        counter.reset(refresh=2, header='new', force=False, color='red')
        assert counter.refresh == 2
        assert counter.header == 'new'
        assert counter.force is False
        assert counter.color == 'red'

    def test_speed_counter_reports_percentage(self):
        counter = progress.SpeedCounter(header='test', max_count=10,
                                        force=True)
        counter.set_count(4)
        counter.set_position(4)
        assert counter.view(flush=True) is True
        counter.reset()

    def test_file_reader_read_byte_chunks(self, tmp_path):
        path = tmp_path / 'chunks.bin'
        path.write_bytes(b'0123456789' * 10)
        reader = progress.FileReader(str(path), header='test')
        chunks = list(reader.read_byte_chunks(7))
        assert b''.join(chunks) == path.read_bytes()
        # the reader closes itself after the last chunk
        # (最後のチャンクの後、リーダー自身がクローズされる)
        assert reader.source is None

    def test_file_reader_read_byte_lines(self, tmp_path):
        path = tmp_path / 'lines.bin'
        path.write_bytes(b'a\nb\nc\n')
        reader = progress.FileReader(str(path), header='test')
        assert list(reader.read_byte_lines()) == [b'a\n', b'b\n', b'c\n']
        assert reader.source is None

    def test_file_reader_rejects_unsupported_sources(self):
        with pytest.raises(TypeError):
            progress.FileReader(42)

    def test_iterator_rejects_non_iterable_sources(self):
        with pytest.raises(TypeError):
            progress.Iterator(42)

    def test_open_returns_a_file_reader(self, tmp_path):
        path = tmp_path / 'f.txt'
        path.write_bytes(b'x')
        reader = progress.open(str(path), header='test')
        assert isinstance(reader, progress.FileReader)
        reader.close()

    def test_view_passes_through_wrappers(self):
        source = [1, 2]
        wrapped = progress.view(iter(source), header='test')
        assert isinstance(wrapped, progress.Iterator)
        assert progress.view(wrapped) is wrapped

    def test_view_wraps_a_path_into_a_file_reader(self, tmp_path):
        path = tmp_path / 'f.txt'
        path.write_bytes(b'x')
        reader = progress.view(str(path))
        assert isinstance(reader, progress.FileReader)
        reader.close()

    def test_view_rejects_unsupported_types(self):
        with pytest.raises(TypeError):
            progress.view(42)

    def test_pipe_view_writes_bytes_to_stdout(self, tmp_path, monkeypatch):
        # bin_stdout is bound at import time, so it is replaced directly
        # instead of being captured through capsysbinary
        # (bin_stdout は import 時に束縛されるため、capsysbinary ではなく
        #  直接差し替える)
        path = tmp_path / 'data.bin'
        path.write_bytes(b'0123456789')
        out = io.BytesIO()
        monkeypatch.setattr(files, 'bin_stdout', out)
        progress.pipe_view([str(path)], mode='bytes', header='test')
        assert out.getvalue() == b'0123456789'

    def test_pipe_view_accepts_a_negative_refresh(self, tmp_path):
        path = tmp_path / 'data.bin'
        path.write_bytes(b'x')
        received = []
        progress.pipe_view([str(path)], mode='bytes', header='test',
                           refresh=-1, outfunc=received.append)
        assert received == [b'x']

    def test_pipe_view_reads_stdin_when_no_files_are_given(
            self, monkeypatch):
        monkeypatch.setattr(files, 'bin_stdin', io.BytesIO(b'streamed\n'))
        out = io.BytesIO()
        monkeypatch.setattr(files, 'bin_stdout', out)
        progress.pipe_view([], mode='bytes')
        assert out.getvalue() == b'streamed\n'


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


class TestDialog:
    def test_get_yes_no_string_varies_by_default(self):
        # 既定値の有無でプロンプト表示が変わること
        assert dialog.get_yes_no_string('yes') == '[Y/n]'
        assert dialog.get_yes_no_string('no') == '[y/N]'
        assert dialog.get_yes_no_string(None) == '[y/n]'

    def test_get_answer_parses_yes_no_and_unknown(self, monkeypatch):
        # y/Y → True, n/N → False, 空行 → 既定値, その他 → None
        for answer, expected in [('y\n', True), ('Y\n', True),
                                 ('n\n', False), ('N\n', False),
                                 ('maybe\n', None)]:
            monkeypatch.setattr('sys.stdin', io.StringIO(answer))
            assert dialog.get_answer() == expected

    def test_get_answer_uses_the_default_for_an_empty_line(self, monkeypatch):
        monkeypatch.setattr('sys.stdin', io.StringIO('\n'))
        assert dialog.get_answer() is None
        assert dialog.get_answer(default='yes') is True
        assert dialog.get_answer(default='no') is False

    def test_ask_continue_keeps_going_on_yes(self, monkeypatch):
        # y → 続行 (例外なく戻る), n → 中断 (SystemExit)
        monkeypatch.setattr('sys.stdin', io.StringIO('y\n'))
        dialog.ask_continue()
        monkeypatch.setattr('sys.stdin', io.StringIO('n\n'))
        with pytest.raises(SystemExit) as exc_info:
            dialog.ask_continue()
        assert exc_info.value.code == 1

    def test_ask_continue_treats_an_empty_line_as_the_default(
            self, monkeypatch):
        monkeypatch.setattr('sys.stdin', io.StringIO('\n'))
        dialog.ask_continue(default='yes')

    def test_ask_continue_if_exist_skips_a_missing_file(self, tmp_path):
        # ファイルが無ければ問い合わせず None を返すこと
        assert dialog.ask_continue_if_exist(str(tmp_path / 'missing.txt')) is None
