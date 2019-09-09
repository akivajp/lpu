#!/usr/bin/env python
# distutils: language=c++
# -*- coding: utf-8 -*-

'''Utilities for viewing I/O progress'''

# Standard libraries
from collections import Iterable
from datetime import datetime
#import io
import sys
import time

# Local libraries
from lpu.backends import safe_cython as cython
from lpu.common import files
from lpu.common import logging
from lpu.common.colors import put_color

logger = logging.getLogger(__name__)

from lpu.common import compat

if sys.version_info.major >= 3:
    bytes_to_str = compat.py3_bytes_to_str
else:
    bytes_to_str = compat.py2_bytes_to_str

# constants
BACK_WHITE = '  \b\b'
DEFAULT_BUFFER_SIZE = 10 * (1024 ** 2) # 10MB
DEFAULT_REFRESH_INTERVAL = 0.5

class SpeedCounter(object):
    def __init__(self, header="", max_count=-1, refresh=DEFAULT_REFRESH_INTERVAL, force=False, color='green'):
        """constructor
        
        Keyword Arguments:
            header {str} -- header of progress line (default: {""})
            max_count {int} -- maximum value known in advance, to compute percentage (default: {-1})
            refresh {[float]} -- refresh interval (default: {DEFAULT_REFRESH_INTERVAL})
            force {bool} -- force mode, to work with non tty output (default: {False})
            color {str} -- text color of progress line (default: {'green'})
        """
        self.refresh = refresh
        self.header = header 
        self.reset()
        self.force = force
        self.max_count = max_count
        self.color = color

    def add(self, count=1, view=False):
        """count up the counter
        
        Keyword Arguments:
            count {int} -- value to count up (default: {1})
            view {bool} -- if true, update the console (default: {False})
        """
        self.count += count
        if view:
            self.view()

    def flush(self):
        """update the console"""
        self.view(flush=True)

    @cython.locals(now = cython.double)
    def reset(self, refresh=None, header=None, force=None, color=None):
        """reset the counter
        
        Keyword Arguments:
            refresh {[bool]} -- new refresh interval (default: {None})
            header {[bool]} -- new header (default: {None})
            force {[bool]} -- new force mode (default: {None})
            color {[bool]} -- new text color (default: {None})
        """
        #cdef double now
        if self.last_time > self.start_time:
            self.flush()
            fobj = None
            if sys.stderr.isatty():
                fobj = sys.stderr
            elif sys.stdout.isatty():
                fobj = sys.stdout
            elif force:
                fobj = sys.stderr
            if fobj:
                fobj.write("\n")
        now = time.time()
        self.start_time = now
        self.last_time  = now
        self.count = 0
        self.last_count = 0
        self.pos = 0
        if refresh != None:
            self.refresh = refresh
        if header != None:
            self.header = header
        if force != None:
            self.force = force
        if color != None:
            self.color = color

    def set_count(self, count, view=False):
        """set the counter value
        
        Arguments:
            count {[int]} -- new count value
        
        Keyword Arguments:
            view {bool} -- if true, update the console (default: {False})
        """
        self.count = count
        if view:
            self.view()

    def set_position(self, position, view=False):
        """set the current position (work with bytes input)
        
        Arguments:
            position {[int]} -- new position
        
        Keyword Arguments:
            view {bool} -- if true, update the console (default: {False})
        """
        self.pos = position
        if view:
            self.view()

    @cython.locals(delta_count = cython.float)
    @cython.locals(delta_time = cython.float)
    @cython.locals(now = cython.double)
    @cython.locals(show_bytes = cython.bint)
    @cython.locals(str_about = str)
    @cython.locals(str_elapsed = str)
    @cython.locals(str_header = str)
    @cython.locals(str_print = str)
    @cython.locals(str_rate = str)
    @cython.locals(str_ratio = str)
    @cython.locals(str_timestamp = str)
    def view(self, flush=False):
        """update the console on condition
        
        Keyword Arguments:
            flush {bool} -- if true, update the console, else decide by elapsed time(default: {False})
        
        Returns:
            [bool] -- true if the console is updated
        """
        now = time.time()
        delta_time  = now - self.last_time
        if not flush:
            if delta_time < self.refresh:
                return False
        fobj = None
        if not self.force:
            if sys.stderr.isatty():
                fobj = sys.stderr
            elif sys.stdout.isatty():
                fobj = sys.stdout
        else:
            fobj = sys.stderr
        if fobj:
            delta_count = self.count - self.last_count
            show_bytes = False
            if self.count == self.pos:
                # bytes mode
                show_bytes = True
            str_rate = about(delta_count / delta_time, show_bytes)
            if self.header:
                str_header = "%s: " % self.header
            else:
                str_header = ""
            if self.max_count > 0:
                if self.pos > 0:
                    str_ratio = "(%.2f%%) " % (self.pos * 100.0 / self.max_count)
                else:
                    str_ratio = "(%.2f%%) " % (self.count * 100.0 / self.max_count)
            else:
                str_ratio = ""
            try:
                #strTimeStamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                #str_timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                str_timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                fobj.write("\r")
                str_elapsed = format_time(now - self.start_time)
                #logging.debug(elapsed)
                #fobj.write("%s%s %s%s [%s/s] [%s]" % (showName, about(self.count,show_bytes), strRatio, strElapsed, strRate, strTimeStamp))
                #fobj.write("[%s] %s%s %s%s [%s/s]" % (strTimeStamp, showName, about(self.count,show_bytes), strRatio, strElapsed, strRate))
                #fobj.write("  \b\b")
                str_about = about(self.count, show_bytes)
                str_print = "[%s] %s%s %s%s [%s/s]%s" % (str_timestamp, str_header, str_about, str_ratio, str_elapsed, str_rate, BACK_WHITE)
                #logging.put_color(str_print, self.color, newline=False)
                str_print = put_color(str_print, self.color)
                #logger.debug(str_print)
                fobj.write(str_print)
            except Exception as e:
                logger.exception(e)
        #if fobj and flush:
        #    fobj.write("\n")
        self.last_time = now
        self.last_count = self.count
        return True

    def __del__(self):
        self.reset()

    def __enter__(self):
        #logger.debug("__enter__")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        #logger.debug("__exit__")
        self.reset()

class FileReader(object):
    def __init__(self, source, header="", refresh=DEFAULT_REFRESH_INTERVAL, force=False):
        if isinstance(source, str):
            #self.source = files.open(source, 'r')
            #self.source = files.open(source, 'rb')
            if not header:
                header = "reading file '%s'" % source
            #self.source = files.open(source, 'rt')
            self.source = files.open(source, 'rb')
        #elif isinstance(source, io.IOBase):
        elif isinstance(source, files.FileType):
            self.source = source
        else:
            raise TypeError("FileReader() expected iterable str or file type, but given %s found" % type(source).__name__)
        size = files.rawsize(self.source)
        #self.counter = ProgressCounter(header=header, refresh=refresh, force=force, max_count=size)
        self.counter = SpeedCounter(header=header, max_count=size, refresh=refresh, force=force)

    #def __del__(self):
    #    print("DEL")
    #    self.close()

    def __dealloc__(self):
        self.close()

    def close(self):
        if self.source:
            #self.counter.flush()
            self.counter.reset()
            self.counter = None
            self.source.close()
            self.source = None

    def read(self, size):
        if self.source:
            buf = self.source.read(size)
            self.counter.add(len(buf))
            try:
                #self.counter.set_position(files.rawtell(self.source))
                self.counter.set_position(self.tell())
            except Exception as e:
                #logger.debug(e)
                pass
            self.counter.view()
            return buf

    @cython.locals(buf = bytes)
    def read_byte_chunks(self, bs = DEFAULT_BUFFER_SIZE):
        #cdef bytes buf
        while True:
            buf = self.read(bs)
            if not buf:
                break
            yield buf
        self.close()

    #cpdef bytes read_byte_line(self):
    def read_byte_line(self):
        return self._read_byte_line(True)
    #cdef bytes _read_byte_line(self, bool countup=False):
    @cython.locals(line = bytes)
    def _read_byte_line(self, countup=False):
        #cdef bytes line
        if self.source:
            line = self.source.readline()
            if countup:
                self.counter.add(len(line))
            try:
                #self.counter.set_position(files.rawtell(self.source))
                self.counter.set_position(self.tell())
            except Exception as e:
                pass
            self.counter.view()
            return line

    @cython.locals(line = bytes)
    def read_byte_lines(self):
        while True:
            line = self.read_byte_line()
            if not line:
                break
            yield line
        self.close()

    @cython.locals(line = bytes)
    def readline(self):
        line = self._read_byte_line(False)
        if line:
            self.counter.add(1)
            return bytes_to_str(line)
        return None

    def tell(self):
        return files.rawtell(self.source)

    def __iter__(self):
        #cdef str line
        while True:
            line = self.readline()
            if not line:
                break
            yield line
        self.close()

    def __enter__(self):
        #logger.debug("__enter__")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        #logger.debug("__exit__")
        self.close()

class Iterator(object):
    def __init__(self, source, header="", refresh=DEFAULT_REFRESH_INTERVAL, force=False, max_count=-1):
        if isinstance(source, Iterable):
            self.source = source
        else:
            raise TypeError("Iterator() expected iterable type, but %s found" % type(source).__name__)
        self.counter = SpeedCounter(header=header, max_count=max_count, refresh=refresh, force=force)

    def __dealloc__(self):
        self.close()

    def close(self):
        if self.source is not None:
            #self.counter.flush()
            self.counter.reset()
            self.counter = None
            self.source = None

    def __iter__(self):
        if self.source is not None:
            for obj in self.source:
                self.counter.add(1, view=True)
                yield obj
        self.close()

    def __len__(self):
        return len(self.source)

    def __enter__(self):
        #logger.debug("__enter__")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        #logger.debug("__exit__")
        self.close()


@cython.locals(show_seconds = cython.uchar)
@cython.locals(show_minutes = cython.uchar)
@cython.locals(show_hours = cython.ulong)
def format_time(seconds):
    seconds = int(seconds)
    show_seconds = seconds % 60
    show_minutes = (seconds / 60) % 60
    show_hours = seconds / (60*60)
    return "%02d:%02d:%02d" % (show_hours,show_minutes,show_seconds)


def about(num, show_bytes=False):
    if show_bytes:
        if num >= 2 ** 30:
            show = num / float(2 ** 30)
            return "%.3fGiB" % show
        elif num >= 2 ** 20:
            show = num / float(2 ** 20)
            return "%.3fMiB" % show
        elif num >= 2 ** 10:
            show = num / float(2 ** 10)
            return "%.3fKiB" % show
        else:
            return "%.3f" % num
    else:
        if num >= 10 ** 9:
            show = num / float(10 ** 9)
            return "%.3fG" % show
        elif num >= 10 ** 6:
            show = num / float(10 ** 6)
            return "%.3fM" % show
        elif num >= 10 ** 3:
            show = num / float(10 ** 3)
            return "%.3fk" % show
        else:
            return "%.3f" % num

def open(path, header=""):
    return FileReader(path, header)

@cython.locals(buf = bytes)
@cython.locals(counter = SpeedCounter)
@cython.locals(delta = long)
@cython.locals(max_count = long)
def pipe_view(filepaths, mode='bytes', header=None, refresh=DEFAULT_REFRESH_INTERVAL, outfunc=None):
    max_count = -1
    delta = 1
    if refresh < 0:
        refresh = DEFAULT_REFRESH_INTERVAL
    infiles = [files.open(fpath, 'rb') for fpath in filepaths]
    if infiles:
        #if mode == 'bytes':
        try:
            max_count = sum(map(files.rawsize, infiles))
        except Exception as e:
            logger.debug(e)
            max_count = 0
    else:
        infiles = [files.bin_stdin]
    counter = SpeedCounter(header=header, refresh=refresh, max_count=max_count)
    for infile in infiles:
        while True:
            buf = infile.read(DEFAULT_BUFFER_SIZE)
            if mode == 'bytes':
                delta = len(buf)
            elif mode == 'lines':
                delta = buf.count(b"\n")
            if not buf:
                break
            #counter.add(view=True)
            if not outfunc:
                files.bin_stdout.write(buf)
            counter.add(delta)
            counter.set_position(counter.pos + len(buf))
            counter.view()
    #counter.flush()
    counter.reset()

def view(source, header=None, max_count=-1, env=True):
    if env and logging.get_quiet_status():
        # as-is (without progress view)
        return source
    elif isinstance(source, (FileReader,Iterator)):
        return source
    #elif isinstance(source, (str,io.IOBase)):
    elif isinstance(source, (str,bytes,files.FileType)):
        if not header:
            #header = "reading file"
            header = "reading file '{}'".format(source)
        return FileReader(source, header)
        #return FileReader(source, header, force=True)
    elif isinstance(source, Iterable):
        if not header:
            header = "iterating"
        if max_count < 0:
            if hasattr(source, '__len__'):
                max_count = len(source)
        return Iterator(source, header, max_count=max_count)
        #return Iterator(source, header, max_count=max_count, force=True)
    else:
        raise TypeError("view() expected file or iterable type, but %s found" % type(source).__name__)
