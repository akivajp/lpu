#!/usr/bin/env python

'''Utilities for viewing I/O progress'''

# Standard libraries
from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Iterator as AbstractIterator
from datetime import datetime
from typing import Any, TextIO, cast
from collections.abc import Callable, Sized
import io
import sys
import time

# Local libraries
from lpu.common import files
from lpu.common import logging
from lpu.common.colors import put_color
from lpu.common.text import to_str as bytes_to_str

logger = logging.getLogger(__name__)

# constants
BACK_WHITE = '  \b\b'
DEFAULT_BUFFER_SIZE = 10 * (1024 ** 2) # 10MB
DEFAULT_REFRESH_INTERVAL = 0.5

class SpeedCounter:
    def __init__(self, header: str = "", max_count: int = -1, refresh: float = DEFAULT_REFRESH_INTERVAL, force: bool = False, color: str = 'green') -> None:
        """constructor
        
        Keyword Arguments:
            header {str} -- header of progress line (default: {""})
            max_count {int} -- maximum value known in advance, to compute percentage (default: {-1})
            refresh {[float]} -- refresh interval (default: {DEFAULT_REFRESH_INTERVAL})
            force {bool} -- force mode, to work with non tty output (default: {False})
            color {str} -- text color of progress line (default: {'green'})
        """
        self.refresh: float = refresh
        self.header: str = header
        self.start_time: float = -1
        self.last_time: float = -1
        # 粗いタイマー (Windows の time.time()) では経過時間が 0.0 のまま
        # になることがあるため、出力の実績は時間ではなくフラグで管理する
        self.printed: bool = False
        self.reset()
        self.force: bool = force
        self.max_count: int = max_count
        self.color: str = color

    def add(self, count: int = 1, view: bool = False) -> None:
        """count up the counter
        
        Keyword Arguments:
            count {int} -- value to count up (default: {1})
            view {bool} -- if true, update the console (default: {False})
        """
        self.count += count
        if view:
            self.view()

    def flush(self) -> None:
        """update the console"""
        self.view(flush=True)

    def reset(self, refresh: float | None = None, header: str | None = None, force: bool | None = None, color: str | None = None) -> None:
        """reset the counter
        
        Keyword Arguments:
            refresh {[bool]} -- new refresh interval (default: {None})
            header {[bool]} -- new header (default: {None})
            force {[bool]} -- new force mode (default: {None})
            color {[bool]} -- new text color (default: {None})
        """
        if self.printed:
            self.flush()
            fobj = self._get_fobj()
            if fobj:
                fobj.write("\n")
        now = time.time()
        self.start_time = now
        self.last_time  = now
        self.count: int = 0
        self.last_count: int = 0
        self.pos: int = 0
        self.printed = False
        if refresh != None:
            self.refresh = refresh
        if header != None:
            self.header = header
        if force != None:
            self.force = force
        if color != None:
            self.color = color
    def _get_fobj(self) -> TextIO | None:
        fobj = None
        if sys.stderr.isatty():
            fobj = sys.stderr
        elif sys.stdout.isatty():
            fobj = sys.stdout
        elif self.force:
            fobj = sys.stderr
        return fobj

    def set_count(self, count: int, view: bool = False) -> None:
        """set the counter value
        
        Arguments:
            count {[int]} -- new count value
        
        Keyword Arguments:
            view {bool} -- if true, update the console (default: {False})
        """
        self.count = count
        if view:
            self.view()

    def set_position(self, position: int, view: bool = False) -> None:
        """set the current position (work with bytes input)
        
        Arguments:
            position {[int]} -- new position
        
        Keyword Arguments:
            view {bool} -- if true, update the console (default: {False})
        """
        self.pos = position
        if view:
            self.view()

    def view(self, flush: bool = False) -> bool:
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
        fobj = self._get_fobj()
        if fobj:
            delta_count = self.count - self.last_count
            show_bytes = False
            if self.count == self.pos:
                # bytes mode
                show_bytes = True
            # Windows では time.time() の分解能が粗く、直前の更新から
            # delta_time が 0.0 のままになることがあるため保護する
            if delta_time > 0:
                str_rate = about(delta_count / delta_time, show_bytes)
            else:
                str_rate = about(0.0, show_bytes)
            if self.header:
                str_header = f"{self.header}: "
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
                str_timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                fobj.write("\r")
                str_elapsed = format_time(now - self.start_time)
                str_about = about(self.count, show_bytes)
                str_print = f"[{str_timestamp}] {str_header}{str_about} {str_ratio}{str_elapsed} [{str_rate}/s]{BACK_WHITE}"
                str_print = put_color(str_print, self.color)
                fobj.write(str_print)
            except Exception as e:
                logger.exception(e)
            self.printed = True
        self.last_time = now
        self.last_count = self.count
        return True

    def __del__(self) -> None:
        self.reset()

    def __enter__(self) -> SpeedCounter:
        #logger.debug("__enter__")
        return self

    def __exit__(self, exception_type: Any, exception_value: Any, traceback: Any) -> None:
        #logger.debug("__exit__")
        self.reset()

class FileReader:
    def __init__(self, source: str | io.IOBase, header: str = "", refresh: float = DEFAULT_REFRESH_INTERVAL, force: bool = False) -> None:
        if isinstance(source, str):
            #self.source = files.open(source, 'r')
            if not header:
                header = f"reading file '{source}'"
            #self.source = files.open(source, 'rt')
            # gzip / raw / buffered ファイルのいずれも入るため Any で受ける
            self.source: Any = files.open(source, 'rb')
        #elif isinstance(source, io.IOBase):
        elif isinstance(source, files.FileType):
            self.source = source
        else:
            raise TypeError(f"FileReader() expected iterable str or file type, but given {type(source).__name__} found")
        size = files.rawsize(self.source)
        #self.counter = ProgressCounter(header=header, refresh=refresh, force=force, max_count=size)
        self.counter = SpeedCounter(header=header, max_count=size, refresh=refresh, force=force)


    def __dealloc__(self) -> None:
        self.close()

    def close(self) -> None:
        if self.source:
            #self.counter.flush()
            self.counter.reset()
            self.counter = None  # type: ignore[assignment]
            self.source.close()
            self.source = None

    def read(self, size: int) -> bytes | None:
        if self.source:
            buf = self.source.read(size)
            self.counter.add(len(buf))
            try:
                #self.counter.set_position(files.rawtell(self.source))
                self.counter.set_position(self.tell())
            except Exception:
                pass
            self.counter.view()
            return cast(bytes, buf)
        return None

    def read_byte_chunks(self, bs: int = DEFAULT_BUFFER_SIZE) -> AbstractIterator[bytes]:
        while True:
            buf = self.read(bs)
            if not buf:
                break
            yield buf
        self.close()

    def read_byte_line(self) -> bytes | None:
        return self._read_byte_line(True)
    def _read_byte_line(self, countup: bool = False) -> bytes | None:
        if self.source:
            line = self.source.readline()
            if countup:
                self.counter.add(len(line))
            try:
                #self.counter.set_position(files.rawtell(self.source))
                self.counter.set_position(self.tell())
            except Exception:
                pass
            self.counter.view()
            return cast(bytes, line)
        return None

    def read_byte_lines(self) -> AbstractIterator[bytes]:
        while True:
            line = self.read_byte_line()
            if not line:
                break
            yield line
        self.close()

    def readline(self) -> str | None:
        line = self._read_byte_line(False)
        if line:
            self.counter.add(1)
            return bytes_to_str(line)
        return None

    def tell(self) -> int:
        return files.rawtell(self.source)

    def __iter__(self) -> AbstractIterator[str]:
        while True:
            line = self.readline()
            if not line:
                break
            yield line
        self.close()

    def __enter__(self) -> FileReader:
        #logger.debug("__enter__")
        return self

    def __exit__(self, exception_type: Any, exception_value: Any, traceback: Any) -> None:
        #logger.debug("__exit__")
        self.close()

class Iterator:
    def __init__(self, source: Iterable[Any], header: str = "", refresh: float = DEFAULT_REFRESH_INTERVAL, force: bool = False, max_count: int = -1) -> None:
        if isinstance(source, Iterable):
            # close() で None を代入するため Optional として扱う
            self.source: Iterable[Any] | None = source
        else:
            raise TypeError(f"Iterator() expected iterable type, but {type(source).__name__} found")
        self.counter = SpeedCounter(header=header, max_count=max_count, refresh=refresh, force=force)

    def __dealloc__(self) -> None:
        self.close()

    def close(self) -> None:
        if self.source is not None:
            #self.counter.flush()
            self.counter.reset()
            self.counter = None  # type: ignore[assignment]
            self.source = None

    def __iter__(self) -> AbstractIterator[Any]:
        if self.source is not None:
            for obj in self.source:
                self.counter.add(1, view=True)
                yield obj
        self.close()

    def __len__(self) -> int:
        # Sized 前提で呼ばれるが、宣言上は Iterable のみ保証できるため cast する
        return len(cast(Sized, self.source))

    def __enter__(self) -> Iterator:
        #logger.debug("__enter__")
        return self

    def __exit__(self, exception_type: Any, exception_value: Any, traceback: Any) -> None:
        #logger.debug("__exit__")
        self.close()


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    show_seconds = int(seconds % 60)
    show_minutes = int((seconds / 60) % 60)
    show_hours = int(seconds / (60*60))
    return f"{show_hours:02d}:{show_minutes:02d}:{show_seconds:02d}"


def about(num: float, show_bytes: bool = False) -> str:
    if show_bytes:
        if num >= 2 ** 30:
            show = num / float(2 ** 30)
            return f"{show:.3f}GiB"
        elif num >= 2 ** 20:
            show = num / float(2 ** 20)
            return f"{show:.3f}MiB"
        elif num >= 2 ** 10:
            show = num / float(2 ** 10)
            return f"{show:.3f}KiB"
        else:
            return f"{num:.3f}"
    else:
        if num >= 10 ** 9:
            show = num / float(10 ** 9)
            return f"{show:.3f}G"
        elif num >= 10 ** 6:
            show = num / float(10 ** 6)
            return f"{show:.3f}M"
        elif num >= 10 ** 3:
            show = num / float(10 ** 3)
            return f"{show:.3f}k"
        else:
            return f"{num:.3f}"

def open(path: str, header: str = "") -> FileReader:
    return FileReader(path, header)

def pipe_view(filepaths: Iterable[str], mode: str = 'bytes', header: str | None = None, refresh: float = DEFAULT_REFRESH_INTERVAL, outfunc: Callable[[bytes], Any] | None = None) -> None:
    max_count = -1
    delta = 1
    if refresh < 0:
        refresh = DEFAULT_REFRESH_INTERVAL
    # gzip / raw / buffered の混在と bin_stdin の代入があるため Any で受ける
    infiles: list[Any] = [files.open(fpath, 'rb') for fpath in filepaths]
    if infiles:
        try:
            max_count = sum(map(files.rawsize, infiles))
        except Exception as e:
            logger.debug(e)
            max_count = 0
    else:
        infiles = [files.bin_stdin]
    counter = SpeedCounter(header=header or '', refresh=refresh, max_count=max_count)
    for infile in infiles:
        while True:
            buf = infile.read(DEFAULT_BUFFER_SIZE)
            if mode == 'bytes':
                delta = len(buf)
            elif mode == 'lines':
                delta = buf.count(b"\n")
            if not buf:
                break
            # Up to 0.2.x outfunc was only used as a flag to suppress the
            # stdout write, and was never actually called.
            # 0.2.x までは outfunc は stdout 出力を抑止するフラグとしてしか
            # 使われておらず、実際には呼び出されていなかった。
            if outfunc:
                outfunc(buf)
            else:
                files.bin_stdout.write(buf)
            counter.add(delta)
            counter.set_position(counter.pos + len(buf))
            counter.view()
    #counter.flush()
    counter.reset()

def view(source: Any, header: str | None = None, max_count: int = -1, env: bool = True) -> Any:
    if env and logging.get_quiet_status():
        # as-is (without progress view)
        return source
    elif isinstance(source, (FileReader,Iterator)):
        return source
    #elif isinstance(source, (str,io.IOBase)):
    elif isinstance(source, (str,bytes,files.FileType)):
        if not header:
            #header = "reading file"
            header = f"reading file '{source}'"  # type: ignore[str-bytes-safe]
        # bytes は FileReader が受け付けず TypeError になる (歴史的経緯の分岐)
        return FileReader(source, header)  # type: ignore[arg-type]
        #return FileReader(source, header, force=True)
    elif isinstance(source, Iterable):
        if not header:
            header = "iterating"
        if max_count < 0:
            if hasattr(source, '__len__'):
                # hasattr による絞り込みは mypy が追わないため cast する
                max_count = len(cast(Sized, source))
        return Iterator(source, header, max_count=max_count)
        #return Iterator(source, header, max_count=max_count, force=True)
    else:
        raise TypeError(f"view() expected file or iterable type, but {type(source).__name__} found")
