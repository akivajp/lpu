#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Customizable logging functions'''

# Standard libraries
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Mapping, cast
import ast
import codecs
import inspect
import logging
import os
import sys
import tokenize
from traceback import FrameSummary
import traceback

from lpu.common import environ
from lpu.common import validation
from lpu.common.colors import put_color
from lpu.common import text

logger = logging.getLogger(__name__)

class LoggingConfig(environ.StackHolder):
    def __init__(self, loggers: logging.Logger | str | Iterable[Any] | None = None) -> None:
        #logger.debug("initializing logging status")
        super(LoggingConfig, self).__init__()
        self.set_loggers(loggers)

    def _reconfigureLogger(self) -> None:
        if self.loggers:
            for logger in self.loggers:
                configureLogger(logger)
        else:
            try:
                import lpu
                configureLogger(lpu.logger)
            except Exception as e:
                lpu.logger.exception(e)

    def set_loggers(self, loggers: logging.Logger | str | Iterable[Any] | None) -> None:
        if loggers:
            set_loggers = set()
            if not isinstance(loggers, (list,tuple)):
                loggers = [loggers]
            for logger in loggers:
                if isinstance(logger, str):
                    #logger = logging.getLogger(logger)
                    logger = getColorLogger(logger)
                set_loggers.add(logger)
            self.loggers: set[logging.Logger] = set_loggers
        else:
            # without this default, a LoggingConfig built without loggers
            # crashed in _reconfigureLogger() with AttributeError
            # (この既定値が無いと、ロガー指定なしで生成した
            #  LoggingConfig が _reconfigureLogger 内で AttributeError
            #  となっていた)
            self.loggers = set()

    def set_debug(self, enable: bool = True) -> None:
        if enable:
            self.set('LPU_DEBUG', '1')
        else:
            self.set('LPU_DEBUG', '0')
        self._reconfigureLogger()
    def unset_debug(self) -> None:
        return self.unset('LPU_DEBUG')

    def set_quiet(self, enable: bool = True) -> None:
        if enable:
            self.set('LPU_QUIET', '1')
        else:
            self.set('LPU_QUIET', '0')
        self._reconfigureLogger()
    def unset_quiet(self) -> None:
        # Up to 0.2.x this was another def unset_debug(), which shadowed the
        # one above and left no way to unset the quiet flag.
        # 0.2.x までは 2 つめの unset_debug() として定義されており、
        # 上の定義を隠したうえ quiet を解除する手段が存在しなかった。
        return self.unset('LPU_QUIET')

    def __enter__(self) -> LoggingConfig:
        #logger.debug("entering logging environment")
        super(LoggingConfig,self).__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        super(LoggingConfig,self).__exit__(exc_type, exc_val, exc_tb)
        #logger.debug("exiting from logging environment")
        self._reconfigureLogger()

def get_debug_status() -> bool:
    mode = environ.get_env('LPU_DEBUG')
    if not mode:
        mode = environ.get_env('DEBUG')
    if not mode:
        return False
    elif mode.lower() in ('', 'false', 'off', '0'):
        return False
    else:
        return True

def get_color_status() -> bool:
    mode = environ.get_env('LPU_COLOR')
    if not mode:
        mode = environ.get_env('COLOR')
    auto = False
    if not mode:
        auto = True
    else:
        if mode.lower() in ('false', 'off', '0'):
            return False
        elif mode.lower() in ('true', 'on', 'always', 'force', '1'):
            return True
        elif mode.lower() in ('', 'auto',):
            auto = True
    if auto:
        return sys.stderr.isatty()
    else:
        return False

def get_quiet_status() -> bool:
    '''report whether quiet mode is enabled

    Note: up to 0.2.x only the QUIET variable was consulted, while
    LoggingConfig.set_quiet() writes LPU_QUIET, so quiet mode was never
    detected. The lookup order now mirrors get_debug_status().

    quiet モードが有効かどうかを返す。
    注意: 0.2.x までは QUIET のみを参照していたが、
    LoggingConfig.set_quiet() が設定するのは LPU_QUIET であるため、
    quiet モードが検出されることが無かった。
    参照順序は get_debug_status() に合わせている。
    '''
    mode = environ.get_env('LPU_QUIET')
    if not mode:
        mode = environ.get_env('QUIET')
    if not mode:
        return False
    elif mode.lower() in ('', 'false', 'off', '0'):
        return False
    else:
        return True

class FilterCondition(logging.Filter):
    def __init__(self, **rules: Any) -> None:
        super(FilterCondition,self).__init__()
        self.rules: dict[str, Any] = rules

    def filter(self, record: logging.LogRecord) -> bool:
        if 'level' in self.rules:
            if self.rules['level'] not in [record.levelname, record.levelno]:
                return False
        return True

def getLevelString(level: int | str) -> str:
    if isinstance(level, int):
        return logging.getLevelName(level)
    elif isinstance(level, str):
        return level
    else:
        validation.check_argument_type(level, 'level', (int, str))
        # チェック関数が型不一致で例外を送出するためここには到達しない
        raise AssertionError('unreachable')

class ColorizingFormatter(logging.Formatter):
    def __init__(self, fmt: str | None = None, datefmt: str | None = None) -> None:
        super(ColorizingFormatter,self).__init__(fmt, datefmt)
        self._format_rules: list[list[Any]] = []
        #self._default_fmt = fmt
        # 既定の書式は文字列前提 (None は ColorizingFormatter の利用形態では無い)
        self._default_fmt: str = cast(str, self._fmt)
        self._colors: dict[str, str] = dict()

    def addFormatRule(self, rule: logging.Filter, fmt: str | None = None) -> None:
        #self._format_rules.append([rule, fmt])
        self._format_rules.insert(0, [rule, fmt])

    def _setColorizedFormat(self, fmt: str, record: logging.LogRecord) -> str:
        self._fmt = fmt
        if sys.version_info.major == 3:
            self._style._fmt = fmt
        return fmt

    #def _colorizeText(self, record, str text):
    def _colorizeText(self, record: logging.LogRecord, text: str) -> str:
        level = record.levelname.lower()
        color_level = self._colors.get(level, None)
        if color_level:
            text = put_color(text, color_level)
        else:
            color_default = self._colors.get('default', None)
            if color_default:
                text = put_color(text, color_default)
        return text

    def format(self, record: logging.LogRecord) -> str:
        fmt_apply: str | None = None
        for flt, fmt in self._format_rules:
            if flt.filter(record):
                if fmt:
                    fmt_apply = fmt
                break
        if fmt_apply:
            self._setColorizedFormat(fmt_apply, record)
        else:
            self._setColorizedFormat(self._default_fmt, record)
        text = super(ColorizingFormatter,self).format(record)
        if sys.version_info.major == 2:
            # Python 2 専用パス (Py3 では到達しない)
            text = codecs.escape_decode(text)[0]  # type: ignore[assignment]
        #logger.info(text)
        #logger.info(type(text))
        return self._colorizeText(record, text)

    def formatStack(self, stack_info: str) -> str:
        #logger.debug(stack_info)
        formatted = stack_info.rstrip()
        formatted = '  ' + formatted.replace('\n', '\n  ')
        color_stack = self._colors.get('stack', None)
        if color_stack:
            formatted = put_color(formatted, color_stack)
        else:
            color_debug = self._colors.get('debug', None)
            if color_debug:
                formatted = put_color(formatted, color_debug)
        return formatted

    def formatException(self, exc_info: tuple[Any, Any, Any]) -> str:
        #logger.debug(exc_info)
        etype, value, tb = exc_info
        list_formatted = traceback.format_exception(etype, value, tb)
        formatted = str.join('', list_formatted).rstrip()
        formatted = '  ' + formatted.replace('\n', '\n  ')
        #formatted = '  ' + str.join('  ', list_formatted).rstrip()
        color_exception = self._colors.get('exception', None)
        if color_exception:
            formatted = put_color(formatted, color_exception)
        else:
            color_error = self._colors.get('error', None)
            if color_error:
                formatted = put_color(formatted, color_error)
        return formatted

    def setColor(self, keyword: str | bytes, color_name: str | None) -> None:
        #if isinstance(keyword, str):
        if isinstance(keyword, str):
            keyword = keyword.lower()
            keyword = keyword.replace('color_', '')
        else:
            # bytes は Py3 では以前の replace でも TypeError になったため検証へ渡す

            #validation.check_argument_type(keyword, 'keyword', str)
            validation.check_argument_type(keyword, 'keyword', (str,bytes))
            # チェック関数が型不一致で例外を送出するためここには到達しない
            raise AssertionError('unreachable')
        if color_name is None:
            # unsetting
            if keyword in self._colors:
                del self._colors[keyword]
        elif isinstance(color_name, str):
            color_name = color_name.lower()
            self._colors[keyword] = color_name
        else:
            validation.check_argument_type(color_name, 'color_name', str)

    def setColors(self, **kwargs: str | None) -> None:
        for key, color in kwargs.items():
            self.setColor(key, color)

    def setLevelFormat(self, level: int | str, fmt: str) -> None:
        level_rule = FilterCondition(level = level)
        self.addFormatRule(level_rule, fmt)

    def setLevelColor(self, level: int | str, color_name: str | None) -> None:
        level_name = getLevelString(level)
        #self._colors[level_name] = color_name
        self.setColor(level_name, color_name)

class CustomLogger(logging.Logger):
    def debug_print(self, val: Any = None, limit: int = 0, offset: int = 0) -> None:
        if logging.DEBUG < self.level:
            return
        # Skip one frame, because this method's own frame is on the stack
        # when running as pure Python.
        # 純 Python 実行時はこのメソッド自身のフレームがスタックに乗るため
        # 1 段分ずらす
        offset += 1
        #stack = traceback.extract_stack(limit=limit)
        stack: list[FrameSummary] = traceback.extract_stack(limit=offset+limit)
        if offset > 0:
            stack = stack[:-offset]
        format = ""
        if limit > 0:
            for path, lineno, func, line in stack:
                line = (_get_cached_line(path, lineno, line) or '').strip()
                s = '\n  file:{}, line:{}, func:{}, code:{}'.format(path, lineno, func, line)
                format += s
        stack = traceback.extract_stack(limit=offset+1)
        path, lineno, func, line = stack[0]
        #expr = _get_cached_expr(path, lineno)
        #frame = sys._getframe(1)
        frame = sys._getframe(offset)
        #args = _seek_args(path, lineno)
        args = _seek_args(path, lineno, None, frame)
        #args = _get_first_arg(frame)
        if args:
            expr = args[0]
        else:
            expr = ""
        #if tree:
        line = text.to_str(line)
        #if val is not None:
        #expr = re.findall(r'\(.*\)$', line)
        #    expr = expr[0][1:-1].strip()
        if expr:
            #if expr.find(',') > 0:
            #    expr = str.join(',', expr.split(',')[:-1]).strip()
            if isinstance(val, (int,float)):
                str_val = '{}({})'.format(type(val).__name__,val)
            elif isinstance(val, str):
                str_val = val
            elif isinstance(val, bytes):
                #repr(val)
                str_val = repr(val)
            else:
                str_val = repr(val)
            if str_val.find('\n') >= 0:
                # multiple lines
                #format = "{} => (see following lines)\n{}".format(expr, str_val) + format
                format = "%s => (see following lines)\n%s"%(expr, str_val) + format
            else:
                # single line
                #format = "{} => {}".format(expr, str_val) + format
                format = "%s => %s"%(expr, str_val) + format
        else:
            format = str(val) + format
        #module_name = inspect.getmodulename(path)
        #if not module_name:
        #    module_name = '__main__'
        #module_name = '__main__'
        #logger = getColorLogger(module_name)
        #logger = getLogger(module_name)
        #logger = colorizeLogger(logger)
        extra = dict(
            filename = path,
            funcName = func,
            lineno = lineno,
        )
        self.debug(format, extra=extra)

    def makeRecord(self, name: str, level: int, fn: str | None, lno: int, msg: Any, args: Any,
                   exc_info: tuple[Any, Any, Any] | None, func: str | None = None,
                   extra: Mapping[str, Any] | None = None, sinfo: str | None = None) -> logging.LogRecord:
        """
        A factory method which can be overridden in subclasses to create
        specialized LogRecords.
        """
        if sys.version_info.major <= 2:
            rv = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func)  # type: ignore[arg-type]
        else: # sys.version_info.major >= 3
            rv = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)  # type: ignore[arg-type]
        if extra is not None:
            for key in extra:
                # accept overwrite!
                rv.__dict__[key] = extra[key]
        return rv

def debug_print(val: Any = None, limit: int = 0, offset: int = 0) -> None:
    # Skip one frame, because this function's own frame is on the stack
    # when running as pure Python.
    # 純 Python 実行時はこの関数自身のフレームがスタックに乗るため 1 段分ずらす
    offset += 1
    logger = getColorLogger('__main__')
    #return logger.debug_print(val, limit)
    return logger.debug_print(val, limit, offset)

DEFAULT_DATE_FORMAT = "%Y/%m/%d %H:%M:%S"
DEFAULT_FORMAT = "[%(asctime)s %(name)s] %(message)s"
DEFAULT_DEBUG_FORMAT = "[%(asctime)s %(name)s %(filename)s:%(funcName)s:%(lineno)s] %(message)s"
DEFAULT_INFO_FORMAT     = DEFAULT_FORMAT
DEFAULT_WARNING_FORMAT  = DEFAULT_FORMAT
DEFAULT_ERROR_FORMAT    = DEFAULT_FORMAT
DEFAULT_CRITICAL_FORMAT = DEFAULT_FORMAT
DEFAULT_DEBUG_COLOR = 'yellow'
DEFAULT_INFO_COLOR  = 'cyan'
#DEFAULT_WARNING_COLOR  = 'purple'
DEFAULT_WARNING_COLOR  = 'yellow'
DEFAULT_ERROR_COLOR    = 'yellow'
DEFAULT_CRITICAL_COLOR = 'red'

def colorizeHandler(handler: logging.Handler,
                    mode: str = 'auto') -> logging.Formatter | logging.Handler:
    # deciding whether to enable colorizing mode (based on arguments, environment)
    if mode == 'auto':
        if isinstance(handler.formatter, ColorizingFormatter):
            # already colorized (itself or any ancestor)
            return handler
        enable = get_color_status()
    else:
        enable = str(mode).lower() in ('1', 'on', 'true', 'always', 'force')
    # setting colorizing formatter
    formatter = ColorizingFormatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
    formatter.setLevelFormat(logging.DEBUG,    DEFAULT_DEBUG_FORMAT)
    formatter.setLevelFormat(logging.INFO,     DEFAULT_INFO_FORMAT)
    formatter.setLevelFormat(logging.WARNING,  DEFAULT_WARNING_FORMAT)
    formatter.setLevelFormat(logging.ERROR,    DEFAULT_ERROR_FORMAT)
    formatter.setLevelFormat(logging.CRITICAL, DEFAULT_CRITICAL_FORMAT)
    if enable:
        formatter.setLevelColor(logging.DEBUG,    DEFAULT_DEBUG_COLOR)
        formatter.setLevelColor(logging.INFO,     DEFAULT_INFO_COLOR)
        formatter.setLevelColor(logging.WARNING,  DEFAULT_WARNING_COLOR)
        formatter.setLevelColor(logging.ERROR,    DEFAULT_ERROR_COLOR)
        formatter.setLevelColor(logging.CRITICAL, DEFAULT_CRITICAL_COLOR)
    handler.setFormatter(formatter)
    return formatter

def _checkLoggerColorized(logger: logging.Logger | None) -> bool:
    while logger:
        for handler in logger.handlers:
            if isinstance(handler.formatter, ColorizingFormatter):
                return True
        # checking ancestors
        logger = logger.parent
    return False

def colorizeLogger(logger: logging.Logger | str, mode: str = 'auto') -> logging.Logger:
    if isinstance(logger, str):
        logger = getLogger(logger)
    handlers = logger.handlers
    for handler in handlers:
        colorizeHandler(handler, mode)
    return logger

def colorize(obj: logging.Logger | logging.Handler) -> logging.Logger | logging.Formatter | logging.Handler | None:
    if isinstance(obj, logging.Logger):
        return colorizeLogger(obj)
    elif isinstance(obj, logging.Handler):
        return colorizeHandler(obj)

def configureLogger(logger: logging.Logger | None, mode: str | int = 'auto') -> logging.Logger | None:
    if not logger:
        return logger
    if mode == 'auto':
        if get_quiet_status():
            logger.setLevel(logging.ERROR)
        elif get_debug_status():
            logger.setLevel(logging.DEBUG)
        else:
            # verbose mode
            logger.setLevel(logging.INFO)
    else:
        logger.setLevel(mode)
    return logger

_cached_lines: dict[str, list[str]] = {}
def _get_cached_line(path: str, lineno: int, fallback: str | None = None, frame: Any = None) -> str | None:
    try:
        if path not in _cached_lines:
            if os.path.exists(path):
                # tokenize.open() honours the PEP 263 coding declaration and
                # defaults to UTF-8. 0.2.x used a bare open(), so on a system
                # whose locale encoding is not UTF-8 any source file with a
                # non-ASCII character failed to be read, and the expression
                # name could not be recovered.
                # tokenize.open() は PEP 263 のコーディング宣言を尊重し、
                # 既定を UTF-8 とする。0.2.x は素の open() を使っていたため、
                # ロケール encoding が UTF-8 でない環境では非 ASCII を含む
                # ソースファイルの読み取りに失敗し、式名を復元できなかった。
                with tokenize.open(path) as f:
                    _cached_lines[path] = f.readlines()
            elif frame is not None:
                # falling back for iPython
                _cached_lines[path], _ = inspect.getsourcelines(frame)
        lines = _cached_lines[path]
        if lineno in range(1, len(lines)+1):
            return lines[lineno-1]
        #return _cached_lines.get(path).get(lineno-1, fallback)
    except Exception:
        pass
    return fallback

_cached_calls: dict[str, list[ast.Call]] = {}
def _get_cached_calls(path: str, lineno: int, fallback: Any = None, frame: Any = None) -> Any:
    if path not in _cached_calls:
        if os.path.exists(path):
            # See the note in _get_cached_line() about tokenize.open()
            # tokenize.open() については _get_cached_line() の注記を参照
            with tokenize.open(path) as f:
                tree = ast.parse(f.read())
        elif frame is not None:
            # falling back for iPython
            tree = ast.parse(inspect.getsource(frame))
        else:
            # No source is available, e.g. when running from stdin, a REPL
            # or exec(). 0.2.x left `tree` undefined and raised NameError,
            # which surfaced as a full traceback in the log.
            # stdin / REPL / exec() のようにソースが取得できない場合。
            # 0.2.x では `tree` が未定義のまま NameError となり、
            # ログにトレースバックがそのまま出力されていた。
            return fallback
        calls = []
        for elem in ast.walk(tree):
            if isinstance(elem, ast.Call):
                calls.append(elem)
        calls.sort(key = _get_call_key)
        _cached_calls[path] = calls
    else:
        calls = _cached_calls[path]
    call = None
    for i, c in enumerate(calls):
        if c.lineno == lineno:
            call = c
            break
        elif c.lineno > lineno:
            if i > 0:
                call = calls[i-1]
            break
    if not call:
        return fallback
    return call
def _get_call_key(call: ast.Call) -> tuple[int, int]:
    return (call.lineno, call.col_offset)

def _seek_args(path: str, lineno: int, fallback: Any = None, frame: Any = None) -> Any:
    try:
        call = _get_cached_calls(path, lineno, fallback, frame)
        _get_cached_line(path, lineno, fallback, frame)
        lines = _cached_lines[path]
        feeder = _get_feeder(lines, call.lineno)
        buf = next(feeder)[call.col_offset:]
        result = _parse_args(buf, feeder)
        return result[0]
    except Exception as e:
        # Recovering the expression is best-effort: without the caller's
        # source (stdin, a REPL, exec(), a frozen build) the value is still
        # printed, just without its label. 0.2.x logged this at ERROR level
        # with a traceback.
        # 式の復元はベストエフォートであり、呼び出し元のソースが無い場合
        # (stdin / REPL / exec() / frozen ビルド) でも値自体は出力される。
        # 0.2.x ではこれを ERROR レベルでトレースバック付きで出力していた。
        logger.debug("could not recover the source expression: %r" % (e,))
        return fallback
def _parse_args(buf: str, feeder: Iterator[str], offset: int = 0, depth: int = 0) -> Any:
    args = []
    expr = ""
    i = offset
    last_char = ""
    while i < len(buf):
        c = buf[i]
        if c == "(":
            if depth > 0:
                expr += "("
            #result = _parse_args(buf, i+1, depth+1)
            result = _parse_args(buf, feeder, i+1, depth+1)
            if depth == 0:
                args += result[0]
                break
            else:
                expr += result[0]
            i = result[1]
        elif c == ")":
            if depth == 0:
                raise Exception("parse error, unexpected depth")
            elif depth == 1:
                break
            elif depth >= 2:
                expr += ")"
            return expr, i
        elif c == ",":
            if depth == 1:
                args.append(expr)
                expr = ""
            else:
                expr += c
        elif c in ["'", '"']:
            result = _seek_str(buf, i)
            expr += result[0]
            i = result[1]
        elif c == " ":
            if last_char != " ":
                expr += c
        elif c == "\n":
            line = next(feeder)
            buf += line
        else:
            if depth > 0:
                expr += c
        last_char = c
        i += 1
    if expr:
        args.append(expr)
    if depth <= 1:
        return args, i
    else:
        return expr, i
def _seek_str(buf: str, offset: int) -> tuple[str, int]:
    i = offset
    if buf[offset:offset+3] == '"""':
        until = '"""'
        i += 3
    elif buf[offset:offset+3] == "'''":
        until = "'''"
        i += 3
    elif buf[offset:offset+1] == '"':
        until = '"'
        i += 1
    elif buf[offset:offset+1] == "'":
        until = "'"
        i += 1
    else:
        return "", i
    expr = until
    check_length = len(until)
    while i < len(buf):
        c = buf[i]
        if c == "\\":
            expr += c
        elif buf[i:i+check_length] == until:
            expr += until
            #i += check_length
            i += (check_length - 1)
            break
        else:
            expr += c
        i += 1
    return expr, i
def _get_feeder(lines: list[str], lineno: int) -> Iterator[str]:
    for n in range(lineno-1, len(lines)):
        yield lines[n]

def getLogger(name: str | None = None) -> CustomLogger:
    CustomLogger.manager.setLoggerClass(CustomLogger)
    # manager.getLogger() の返り値の型は Logger だが、クラスが
    # CustomLogger に設定済みであるためキャストする
    # manager.getLogger() の typeshed は str を要求するが None (root) も渡せる
    return cast(CustomLogger, CustomLogger.manager.getLogger(cast(str, name)))

def getColorLogger(name: str, level_mode: str = 'auto',
                   add_handler: str | logging.Handler | None = 'auto') -> CustomLogger:
    logger = getLogger(name)
    if level_mode != 'auto':
        # configureLogger は truthy な logger をそのまま返すため実質非 None
        logger = cast(CustomLogger, configureLogger(logger, mode=level_mode))
    #logger.debug_print = MethodType(_debug_print, logger, logging.Logger)
    if add_handler == 'auto':
        if _checkLoggerColorized(logger):
            add_handler = None
        else:
            add_handler = logging.StreamHandler()
    if add_handler:
        # duplication check
        for handler in logger.handlers:
            if handler is add_handler:
                add_handler = None
        if add_handler:
            # 'auto' の処理後に Handler か None に確定している
            logger.addHandler(cast(logging.Handler, add_handler))
            if level_mode == 'auto':
                configureLogger(logger, mode=level_mode)
    # colorizeLogger は logger 自身を返すため CustomLogger と同一
    return cast(CustomLogger, colorizeLogger(logger))

# global environ
def using_config(loggers: logging.Logger | str | Iterable[Any],
                 debug: bool | None = None, quiet: bool | None = None) -> LoggingConfig:
    env_layer = environ.push(LoggingConfig)
    env_layer.set_loggers(loggers)
    if debug is not None:
        env_layer.set_debug(debug)
    if quiet is not None:
        # Up to 0.2.x this passed `debug` here, so the quiet flag was
        # never applied.
        # 0.2.x まではここで `debug` を渡していたため、quiet の指定が
        # 反映されなかった。
        env_layer.set_quiet(quiet)
    return env_layer

# importing from system logging module
NOTSET   = logging.NOTSET
INFO     = logging.INFO
DEBUG    = logging.DEBUG
WARNING  = logging.WARNING
ERROR    = logging.ERROR
CRITICAL = logging.CRITICAL

Filter = logging.Filter
StreamHandler = logging.StreamHandler
FileHandler = logging.FileHandler
