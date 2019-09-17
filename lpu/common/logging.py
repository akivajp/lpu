#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''Customizable logging functions'''

# Standard libraries
import ast
import codecs
import re
import sys
import traceback

from lpu.backends import safe_cython as cython
from lpu.backends import safe_logging as logging

#import lpu
from lpu.common import environ
from lpu.common import validation
from lpu.common.colors import put_color
from lpu.common import compat
from lpu.common.compat import MethodType

logger = logging.getLogger(__name__)

class LoggingStatus(environ.StackHolder):
    #def __init__(self, logger=None):
    def __init__(self, loggers=None):
        #print(LoggingStatus)
        #print(type(LoggingStatus))
        #logger.debug("initializing logging status")
        super(LoggingStatus, self).__init__()
        #self.loggers = None
        self.set_loggers(loggers)

    def _reconfigureLogger(self):
        if self.loggers:
            for logger in self.loggers:
                configureLogger(logger)
        else:
            try:
                import lpu
                configureLogger(lpu.logger)
            except Exception as e:
                pass

    def set_loggers(self, loggers):
        if loggers:
            set_loggers = set()
            if not isinstance(loggers, (list,tuple)):
                loggers = [loggers]
            for logger in loggers:
                if isinstance(logger, str):
                    logger = logging.getLogger(logger)
                set_loggers.add(logger)
            self.loggers = set_loggers

    def set_debug(self, enable=True):
        if enable:
            self.set('LPU_DEBUG', '1')
        else:
            self.set('LPU_DEBUG', '0')
        self._reconfigureLogger()
    def unset_debug(self):
        return self.unset('LPU_DEBUG')

    def set_quiet(self, enable=True):
        if enable:
            self.set('LPU_QUIET', '1')
        else:
            self.set('LPU_QUIET', '0')
        self._reconfigureLogger()
    def unset_debug(self):
        return self.unset('LPU_QUIET')

    def __enter__(self):
        #logger.debug("entering logging environment")
        super(LoggingStatus,self).__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(LoggingStatus,self).__exit__(exc_type, exc_val, exc_tb)
        #logger.debug("exiting from logging environment")
        self._reconfigureLogger()

def get_debug_status():
    mode = environ.get_env('LPU_DEBUG')
    if not mode:
        mode = environ.get_env('DEBUG')
    if not mode:
        return False
    elif mode.lower() in ('', 'false', 'off', '0'):
        return False
    else:
        return True

def get_color_status():
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

def get_quiet_status():
    mode = environ.get_env('QUIET')
    if not mode:
        return False
    else:
        if mode.lower() in ('', 'false', '0'):
            return False
        elif mode.lower() in ('true', '1'):
            return True
    return False

class FilterCondition(logging.Filter):
    def __init__(self, **rules):
        super(FilterCondition,self).__init__()
        self.rules = rules

    def filter(self, record):
        if 'level' in self.rules:
            if self.rules['level'] not in [record.levelname, record.levelno]:
                return False
        return True

def getLevelString(level):
    if isinstance(level, int):
        return logging.getLevelName(level)
    elif isinstance(level, str):
        return level
    else:
        validation.check_argument_type(level, 'level', (int, str))

class ColorizingFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super(ColorizingFormatter,self).__init__(fmt, datefmt)
        self._format_rules = []
        #self._default_fmt = fmt
        self._default_fmt = self._fmt
        self._colors = dict()

    def addFormatRule(self, rule, fmt=None):
        #print("adding format: {}".format(fmt))self._fmt
        #print("adding filter: {}".format(filter))
        #self._format_rules.append([rule, fmt])
        self._format_rules.insert(0, [rule, fmt])

    def _setColorizedFormat(self, fmt, record):
        self._fmt = fmt
        if sys.version_info.major == 3:
            self._style._fmt = fmt
        return fmt

    #cpdef str _colorizeText(self, record, str text):
    #def _colorizeText(self, record, str text):
    def _colorizeText(self, record, text):
        #cdef object color_default
        level = record.levelname.lower()
        color_level = self._colors.get(level, None)
        if color_level:
            text = put_color(text, color_level)
        else:
            color_default = self._colors.get('default', None)
            if color_default:
                text = put_color(text, color_default)
        return text

    @cython.locals(text = str)
    def format(self, record):
        #cdef str text
        #print("formatting... {}".format(record))
        fmt_apply = None
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
            text = codecs.escape_decode(text)[0]
        #logger.info(text)
        #logger.info(type(text))
        return self._colorizeText(record, text)

    def formatStack(self, stack_info):
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

    def formatException(self, exc_info):
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

    def setColor(self, keyword, color_name):
        #if isinstance(keyword, str):
        if isinstance(keyword, (str,bytes)):
            keyword = keyword.lower()
            keyword = keyword.replace('color_', '')
        else:
            #validation.check_argument_type(keyword, 'keyword', str)
            validation.check_argument_type(keyword, 'keyword', (str,bytes))
        if color_name is None:
            # unsetting
            if keyword in self._colors:
                del self._colors[keyword]
        elif isinstance(color_name, str):
            color_name = color_name.lower()
            self._colors[keyword] = color_name
        else:
            validation.check_argument_type(color_name, 'color_name', str)

    def setColors(self, **kwargs):
        for key, color in kwargs.items():
            self.setColor(key, color)

    def setLevelFormat(self, level, fmt):
        level_name = getLevelString(level)
        level_rule = FilterCondition(level = level)
        self.addFormatRule(level_rule, fmt)

    def setLevelColor(self, level, color_name):
        level_name = getLevelString(level)
        #self._colors[level_name] = color_name
        self.setColor(level_name, color_name)

class CustomLogger(logging.Logger):
    #cpdef _debug_print(self, val=None, limit=0):
    def debug_print(self, val=None, limit=0, offset=0):
        if logging.DEBUG < self.level:
            return
        if not cython.compiled:
            offset += 1
        #stack = traceback.extract_stack(limit=limit)
        stack = traceback.extract_stack(limit=offset+limit)
        #print("offset", offset)
        if offset > 0:
            stack = stack[:-offset]
        format = ""
        if limit > 0:
            for path, lineno, func, line in stack:
                line = _get_cached_line(path, lineno, line).strip()
                s = '\n  file:{}, line:{}, func:{}, code:{}'.format(path, lineno, func, line)
                format += s
        stack = traceback.extract_stack(limit=offset+1)
        #for path, lineno, func, line in stack:
        #    print(path, lineno, func, line)
        path, lineno, func, line = stack[0]
        #print(line)
        #line = _get_cached_line(path, lineno, line).strip()
        #print("line", line)
        #expr = _get_cached_expr(path, lineno)
        args = _seek_args(path, lineno)
        if args:
            expr = args[0]
        else:
            expr = ""
        #print(expr)
        #if tree:
        #    for elem in ast.walk(tree):
        #        if isinstance(elem, ast.Call):
        #            print(elem)
        #            print(elem.lineno)
        line = compat.to_str(line)
        #if val is not None:
        #expr = re.findall(r'\(.*\)$', line)
        #if expr:
        #    expr = expr[0][1:-1].strip()
        if expr:
            #if expr.find(',') > 0:
            #    expr = str.join(',', expr.split(',')[:-1]).strip()
            if sys.version_info.major == 2:
                #expr = compat.to_unicode(expr)
                if isinstance(val, unicode):
                    val = compat.to_str(val)
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

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """
        A factory method which can be overridden in subclasses to create
        specialized LogRecords.
        """
        if sys.version_info.major <= 2:
            rv = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func)
        else: # sys.version_info.major >= 3
            rv = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra is not None:
            for key in extra:
                # accept overwrite!
                rv.__dict__[key] = extra[key]
        return rv

def debug_print(val=None, limit=0, offset=0):
    if not cython.compiled:
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

def colorizeHandler(handler, mode='auto'):
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

#cdef _checkLoggerColorized(logger):
def _checkLoggerColorized(logger):
    while logger:
        for handler in logger.handlers:
            if isinstance(handler.formatter, ColorizingFormatter):
                return True
        # checking ancestors
        logger = logger.parent
    return False

def colorizeLogger(logger, mode='auto'):
    if isinstance(logger, str):
        logger = getLogger(logger)
    handlers = logger.handlers
    for handler in handlers:
        colorizeHandler(handler, mode)
    return logger

def colorize(obj):
    if isinstance(obj, logging.Logger):
        return colorizeLogger(obj)
    elif isinstance(obj, logging.Handler):
        return colorizeHandler(obj)

def configureLogger(logger, mode='auto'):
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

_cached_lines = {}
#cdef _get_cached_line(path, lineno, fallback):
def _get_cached_line(path, lineno, fallback):
    try:
        if path not in _cached_lines:
            _cached_lines[path] = open(path).readlines()
        lines = _cached_lines[path]
        if lineno in range(1, len(lines)+1):
            return lines[lineno-1]
        #return _cached_lines.get(path).get(lineno-1, fallback)
    except:
        pass
    return fallback

#_cached_trees = {}
_cached_calls = {}
def _get_cached_calls(path, lineno, fallback=None):
    if path not in _cached_calls:
        #_cached_trees[path] = ast.parse(open(path).read())
        tree = ast.parse(open(path).read())
        calls = []
        for elem in ast.walk(tree):
            if isinstance(elem, ast.Call):
                calls.append(elem)
        calls.sort(key = lambda e: (e.lineno, e.col_offset))
        #_cached_trees = 
        _cached_calls[path] = calls
    else:
        calls = _cached_calls[path]
    call = None
    #next_call = None
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

def _seek_args(path, lineno, fallback=None):
    try:
        call = _get_cached_calls(path, lineno, fallback)
        lines = _cached_lines[path]
        def feed(lines, lineno):
            for n in range(lineno-1, len(lines)):
                yield lines[n]
        feeder = feed(lines, call.lineno)
        def seek_str(buf, offset):
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
        def parse_args(buf, offset=0, depth=0):
            args = []
            expr = ""
            i = offset
            last_char = ""
            while i < len(buf):
                #print(i, depth, buf[i:].strip())
                c = buf[i]
                if c == "(":
                    if depth > 0:
                        expr += "("
                    result = parse_args(buf, i+1, depth+1)
                    #print("result: {}".format(result))
                    if depth == 0:
                        #print("breaking")
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
                    #print("expr: {}".format(expr))
                    return expr, i
                elif c == ",":
                    if depth == 1:
                        args.append(expr)
                        expr = ""
                    else:
                        expr += c
                    #print(depth, args, expr)
                elif c in ["'", '"']:
                    result = seek_str(buf, i)
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
            #print(depth, args, expr, i)
            if depth <= 1:
                #print(depth, args, i)
                return args, i
            else:
                #print(depth, expr, i)
                return expr, i
        buf = next(feeder)[call.col_offset:]
        result = parse_args(buf)
        #print(result)
        return result[0]
    except Exception as e:
        #print(e)
        logger.exception(e)
        return fallback

def getColorLogger(name, level_mode='auto', add_handler='auto'):
    #logger = logging.getLogger(name)
    logger = getLogger(name)
    if level_mode is not 'auto':
        logger = configureLogger(logger, mode=level_mode)
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
            logger.addHandler(add_handler)
            if level_mode is 'auto':
                configureLogger(logger, mode=level_mode)
    return colorizeLogger(logger)

# global environ
#def push_environ(logger):
#cpdef using_config(logger, debug=None, quiet=None):
#cpdef using_config(loggers, debug=None, quiet=None):
def using_config(loggers, debug=None, quiet=None):
    env_layer = environ.push(LoggingStatus)
    env_layer.set_loggers(loggers)
    if debug is not None:
        env_layer.set_debug(debug)
    if quiet is not None:
        env_layer.set_quiet(debug)
    return env_layer
#env = push_environ(logger)
#env = using_config(None)

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

#getLogger = logging.getLogger
def getLogger(name=None):
    return CustomLogger(name)
