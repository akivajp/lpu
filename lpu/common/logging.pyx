# distutils: language=c++
# -*- coding: utf-8 -*-

'''Customizable logging functions'''

# Standard libraries
import sys
import traceback

from lpu.__system__ import logging

from lpu.common import environ
from lpu.common import validation
from lpu.common.colors import put_color

logger = logging.getLogger(__name__)

#cdef _update_module_logger():
#    try:
#        from lpu.common.logging import configureLogger
#        configureLogger(lpu.logger)
#    except Exception as e:
#        pass

class LoggingStatus(environ.StackHolder):
    def __init__(self, logger=None):
        super(LoggingStatus,self).__init__(self)
        self.logger = None

    def set_logger(self, logger):
        self.logger = logger

    def set_debug(self, enable=True):
        if enable:
            self.set('DEBUG', '1')
        else:
            self.set('DEBUG', '0')
        configureLogger(logger)
        configureLogger(self.logger)
    def unset_debug(self):
        return self.clear('DEBUG')

    def set_quiet(self, enable=True):
        if enable:
            self.set('QUIET', '1')
        else:
            self.set('QUIET', '0')
        configureLogger(logger)
        configureLogger(self.logger)
    def unset_debug(self):
        return self.clear('QUIET')

    def __enter__(self):
        logger.debug("entering logging environment")
        super(LoggingStatus,self).__enter__()
        #configureLogger(logger)
        #configureLogger(self.logger)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(LoggingStatus,self).__exit__(exc_type, exc_val, exc_tb)
        logger.debug("exiting from logging environment")
        configureLogger(logger)
        configureLogger(self.logger)

def get_debug_status():
    mode = environ.get_env('DEBUG')
    if not mode:
        return False
    elif mode.lower() in ('', 'false', 'off', '0'):
        return False
    else:
        return True

def get_color_status():
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

    def format(self, record):
        #print("formatting... {}".format(record))
        fmt_apply = None
        for flt, fmt in self._format_rules:
            if flt.filter(record):
                #print("filter: {}".format(flt))
                #print("format: {}".format(fmt))
                #print("record: {}".format(record))
                if fmt:
                    #self._style._fmt = self._fmt = fmt
                    #setFormat(self, fmt)
                    #self._setColorizedFormat(fmt, record)
                    fmt_apply = fmt
                break
        if fmt_apply:
            self._setColorizedFormat(fmt_apply, record)
        else:
            self._setColorizedFormat(self._default_fmt, record)
        #print("format to apply: {}".format(fmt_apply))
        return super(ColorizingFormatter,self).format(record)

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
        #print("keyword: {}".format(keyword))
        #print("color name: {}".format(color_name))
        if isinstance(keyword, str):
            keyword = keyword.lower()
            keyword = keyword.replace('color_', '')
        else:
            validation.check_argument_type(keyword, 'keyword', str)
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

    def _setColorizedFormat(self, fmt, record):
        level = record.levelname.lower()
        color_level = self._colors.get(level, None)
        #print("level: {}".format(level))
        #print("level color: {}".format(color_level))
        if color_level:
            fmt = put_color(fmt, color_level)
        else:
            color_default = self._colors.get('default', None)
            #print("default color: {}".format(color_default))
            if color_default:
                fmt = put_color(fmt, color_default)
        self._fmt = fmt
        if sys.version_info.major == 3:
            self._style._fmt = fmt

DEFAULT_DATE_FORMAT = "%Y/%m/%d %H:%M:%S"
DEFAULT_FORMAT = "[%(asctime)s %(name)s %(filename)s:%(funcName)s:%(lineno)s] %(message)s"
DEFAULT_INFO_FORMAT = "[%(asctime)s] %(message)s"
DEFAULT_DEBUG_COLOR = 'yellow'
DEFAULT_INFO_COLOR  = 'cyan'
#DEFAULT_WARNING_COLOR  = 'purple'
DEFAULT_WARNING_COLOR  = 'yellow'
DEFAULT_ERROR_COLOR    = 'yellow'
DEFAULT_CRITICAL_COLOR = 'red'

cdef _checkColorized(logger):
    while logger:
        for handler in logger.handlers:
            if isinstance(handler.formatter, ColorizingFormatter):
                return True
        # checking ancestors
        logger = logger.parent
    return False

def colorizeLogger(logger, mode='auto'):
    # deciding whether to enable colorizing mode (based on arguments, environment)
    if mode == 'auto':
        if _checkColorized(logger):
            # already colorized (itself or any ancestor)
            return logger
        enable = get_color_status()
    else:
        enable = str(mode).lower() in ('1', 'on', 'true', 'always', 'force')
    # setting colorizing formatter
    handlers = logger.handlers
    if len(handlers) == 0:
        logger.addHandler(logging.StreamHandler())
    formatter = ColorizingFormatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
    formatter.setLevelFormat(logging.INFO, DEFAULT_INFO_FORMAT)
    if enable:
        formatter.setLevelColor(logging.DEBUG,    DEFAULT_DEBUG_COLOR)
        formatter.setLevelColor(logging.INFO,     DEFAULT_INFO_COLOR)
        formatter.setLevelColor(logging.WARNING,  DEFAULT_WARNING_COLOR)
        formatter.setLevelColor(logging.ERROR,    DEFAULT_ERROR_COLOR)
        formatter.setLevelColor(logging.CRITICAL, DEFAULT_CRITICAL_COLOR)
    for handler in handlers:
        if not isinstance(handler.formatter, ColorizingFormatter):
            handler.setFormatter(formatter)
    return logger

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
    return logger

def getColorLogger(name, level_mode='auto', color_mode='auto'):
    logger = logging.getLogger(name)
    logger = configureLogger(logger, mode=level_mode)
    return colorizeLogger(logger, mode=color_mode)

# global environ
def push_environ(logger):
    layer = environ.push(LoggingStatus)
    layer.set_logger(logger)
    return layer
env_layer = push_environ(logger)

# importing from system logging module
INFO     = logging.INFO
DEBUG    = logging.DEBUG
WARNING  = logging.WARNING
ERROR    = logging.ERROR
CRITICAL = logging.CRITICAL

Filter = logging.Filter
StreamHandler = logging.StreamHandler

debug     = logging.debug
info      = logging.info
warning   = logging.warning
error     = logging.error
critical  = logging.critical
exception = logging.exception
getLogger = logging.getLogger

