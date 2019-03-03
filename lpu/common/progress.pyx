# distutils: language=c++
# -*- coding: utf-8 -*-

'''Utilities for viewing I/O progress'''

# C++ setting
from libcpp cimport bool
from libcpp.string cimport string

# Standard libraries
from collections import Iterable
from datetime import datetime
#import io
import sys
import time

# Local libraries
from lpu.common import files
from lpu.common import logging
from lpu.common.colors import put_color
from lpu.common.logging import debug_print as dprint

logger = logging.getLogger(__name__)

from lpu.common cimport compat

if sys.version_info.major >= 3:
    bytes_to_str = compat.py3_bytes_to_str
else:
    bytes_to_str = compat.py2_bytes_to_str

cdef long DEFAULT_BUFFER_SIZE = 10 * (1024 ** 2) # 10MB

#cdef long BUFFER_SIZE = 4096
cdef str BACK_WHITE = '  \b\b'

#cdef double REFRESH = 1
cdef double REFRESH = 0.5

#cdef class ProgressCounter(object):
cdef class SpeedCounter(object):
    cdef readonly bool force
    cdef readonly str header
    cdef readonly double refresh
    cdef readonly double start_time, last_time
    cdef readonly long count, pos, last_count, max_count
    cdef readonly str color

    def __cinit__(self, str header="", long max_count=-1, double refresh=REFRESH, bool force=False, str color='green'):
        #logging.log("__CINIT__", color="cyan")
        self.refresh = refresh
        self.header = header 
        self.reset()
        self.force = force
        self.max_count = max_count
        self.color = color

    def add(self, unsigned long count=1, bool view=False):
        self.count += count
        if view:
            self.view()

    def flush(self):
        self.view(flush=True)

    def reset(self, refresh=None, header=None, force=None, color=None):
        cdef double now
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

    def set_count(self, unsigned long count, bool view=False):
        self.count = count
        if view:
            self.view()

    def set_position(self, unsigned long position, bool view=False):
        self.pos = position
        if view:
            self.view()

    def view(self, bool flush=False):
        cdef double now, delta_time, delta_count
        cdef str str_elapsed, str_rate, str_ratio
        cdef str str_timestamp, str_header, str_about
        cdef str str_print
        cdef bool show_bytes
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
                #dprint(str_print)
                #dprint(type(str_print))
                #dprint(self.color)
                #dprint(type(self.color))
                logger.exception(e)
        #if fobj and flush:
        #    fobj.write("\n")
        self.last_time  = now
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

#cdef class ProgressReader(object):
cdef class FileReader(object):
    #cdef ProgressCounter counter
    cdef SpeedCounter counter
    cdef object source

    def __cinit__(self, source, str header="", double refresh=REFRESH, bool force=False):
    #def __cinit__(self, source, header="", double refresh=REFRESH, bool force=False):
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

    cpdef close(self):
        if self.source:
            #self.counter.flush()
            self.counter.reset()
            self.counter = None
            self.source.close()
            self.source = None

    cpdef bytes read(self, size):
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

    def read_byte_chunks(self, bs = DEFAULT_BUFFER_SIZE):
        cdef bytes buf
        while True:
            buf = self.read(bs)
            if not buf:
                break
            yield buf
        self.close()

    cdef bytes _read_byte_line(self, bool countup=False):
        cdef bytes line
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
    cpdef bytes read_byte_line(self):
        return self._read_byte_line(True)

    def read_byte_lines(self):
        cdef bytes line
        while True:
            line = self.read_byte_line()
            if not line:
                break
            yield line
        self.close()

    cpdef str readline(self):
        cdef bytes line
        line = self._read_byte_line(False)
        if line:
            self.counter.add(1)
            return bytes_to_str(line)
        return None

    cpdef long tell(self) except *:
        return files.rawtell(self.source)

    def __iter__(self):
        cdef str line
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

cdef class Iterator(object):
    cdef SpeedCounter counter
    cdef object source

    def __cinit__(self, source, str header="", double refresh=REFRESH, bool force=False, long max_count=-1):
        if isinstance(source, Iterable):
            self.source = source
        else:
            raise TypeError("Iterator() expected iterable type, but %s found" % type(source).__name__)
        self.counter = SpeedCounter(header=header, max_count=max_count, refresh=refresh, force=force)

    def __dealloc__(self):
        self.close()

    cdef close(self):
        if self.source is not None:
            #self.counter.flush()
            self.counter.reset()
            self.counter = None
            self.source = None

    def __iter__(self):
        cdef object obj
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

cdef format_time(seconds):
    cdef unsigned char show_seconds, show_minutes
    cdef unsigned long show_hours
    seconds = int(seconds)
    show_seconds = seconds % 60
    show_minutes = (seconds / 60) % 60
    show_hours = seconds / (60*60)
    return "%02d:%02d:%02d" % (show_hours,show_minutes,show_seconds)

def about(num, bool show_bytes = False):
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

cpdef open(path, str header=""):
    return FileReader(path, header)

cpdef pipe_view(filepaths, mode='bytes', str header=None, refresh=REFRESH, outfunc=None):
    #cdef str strBuf
    cdef bytes buf
    cdef long max_count = -1
    cdef long delta = 1
    cdef SpeedCounter counter
    if refresh < 0:
        refresh = REFRESH
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

#cpdef view(source, str header = None, long max_count = -1, env = True):
#cpdef view(source, strtype header=None, long max_count=-1, bool env=True):
cpdef view(source, header=None, long max_count=-1, bool env=True):
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

