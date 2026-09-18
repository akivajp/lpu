#!/usr/bin/env python

'''Auxiliary functions for file I/O'''

from __future__ import annotations

# Standard libraries
import gzip
import io
import os.path
import sys
import tempfile
import time
from collections.abc import Iterable
from typing import Any

# Local libraries
from lpu.common import logging

logger = logging.getLogger(__name__)

#env = os.environ
#env['LC_ALL'] = 'C'

DEFAULT_BUFFER_SIZE = 10 * (1024 ** 2) # 10MB

_open = open

# Python 2 compatibility shims were removed: the package requires Python
# 3.10+ (requires-python), so the sys.version_info check below always takes
# the Python 3 branch.
# (Python 2 互換の代替定義は削除。requires-python により 3.10 以上が前提で、
#  下記のバージョン分岐は常に Python 3 側を通るため)
bin_stdin  = sys.stdin.buffer
bin_stdout = sys.stdout.buffer
bin_stderr = sys.stderr.buffer
FileType: type[io.IOBase] = io.IOBase

#def autoCat(filenames, target):
def concat_into(
    filenames: str | list[str],
    target: str,
    progress: bool = True,
) -> None:
    '''
        concatenate and copy files into target file (expanding for compressed ones)
    '''
    if not isinstance(filenames, list):
        # a single path is accepted as well
        filenames = [filenames]
    f_out = open(target, 'wb')
    if progress:
        from lpu.common.progress import view as pview
        logger.info(f"writing into: {target}")
        for filename in filenames:
            f_in = pview(filename, header=f"  transfering from: {filename}")
            for line in f_in.read_byte_chunks(DEFAULT_BUFFER_SIZE):
                f_out.write(line)
            f_in.close()
    else:
        for filename in filenames:
            f_in = open(filename, 'rb')
            for line in f_in:
                f_out.write(line)
            f_in.close()
    f_out.close()

def castFile(anyFile: Any) -> io.IOBase:
    '''try to convert any argument to file like object
    * if given file like object, then return itself
    * otherwise (e.g. given file path string), try to open it and return file object'''
    if hasattr(anyFile, 'read'):
        return anyFile
    else:
        return open(anyFile)

def getContentSize(path: str) -> int:
    '''get the file content size (expanded size for compressed one)'''
    try:
        f_in = _open(path, 'rb')
        if is_gzipped(path):
            # In the gzip format, the last 4 bytes (the ISIZE field) hold
            # the uncompressed size modulo 2^32, little-endian. The previous
            # implementation used gzip.read32(), which has since been
            # removed, so it always raised and returned -1.
            # gzip 形式では末尾 4 バイト (ISIZE フィールド) に展開後サイズを
            # 2^32 で割った余りがリトルエンディアンで格納されている。
            # 旧実装は既に削除された gzip.read32() を使っていたため、
            # 常に例外となって -1 を返していた。
            f_in.seek(-4, 2)
            isize = int.from_bytes(f_in.read(4), 'little')
            f_in.close()
            return isize
        else:
            f_in.seek(0, 2)
            pos = f_in.tell()
            f_in.close()
            return pos
    except Exception:
        return -1


def get_ext(filename: str) -> str:
    '''get the extension of given file'''
    (name, ext) = os.path.splitext(filename)
    return ext

#def isIOType(obj):
#    #return isinstance(obj, (io.IOBase,file))
#    return isinstance(obj, FileType)

def is_gzipped(filename: str) -> bool:
    '''check whether the given file is compressed by gzip or not

    Only the 2-byte magic number (0x1f 0x8b) at the head is checked.
    The previous implementation actually decompressed one line, which
    caused wasteful I/O and decompression for huge files.

    先頭 2 バイトのマジックナンバー (0x1f 0x8b) のみを確認する。
    旧実装は実際に 1 行を解凍していたため、巨大なファイルに対して
    無駄な I/O と展開処理が発生していた。
    '''
    try:
        with _open(filename, 'rb') as f:
            return f.read(2) == b'\x1f\x8b'
    except Exception:
        return False

def is_mode(fobj: Any, mode: str) -> bool | None:
    # Python 3.12 以前の gzip.GzipFile は .mode 属性が int (READ=1 /
    # WRITE=2) で、3.13 以降は 'rb' 等の文字列になるため正規化する。
    # (GzipFile は常にバイナリとして開かれる)
    fmode = fobj.mode
    if isinstance(fmode, int):
        if fmode == 1:
            fmode = 'rb'
        elif fmode == 2:
            fmode = 'wb'
        else:
            fmode = ''
    if mode in ('r', 'read'):
        return fmode.find('r') >= 0
    elif mode in ('w', 'write'):
        return fmode.find('w') >= 0
    elif mode in ('b', 'binary'):
        if fmode.find('b') >= 0:
            return True
        elif fmode.find('t') >= 0:
            return False
        else:
            return sys.version_info.major < 3
    elif mode in ('t', 'text'):
        if fmode.find('t') >= 0:
            return True
        elif fmode.find('b') >= 0:
            return False
        else:
            return sys.version_info.major >= 3
    return None

def load(
    filepath_or_buffer: str | Any,
    out_buffer: io.IOBase,
    progress: bool = True,
    bs: int = DEFAULT_BUFFER_SIZE,
) -> io.IOBase:
    '''load all the content of given file (expand if compressed)'''
    if isinstance(filepath_or_buffer, str):
        # file path
        filepath = filepath_or_buffer
        buf = _open(filepath, 'rb')
        if progress:
            from lpu.common.progress import SpeedCounter
            header = f"loading file '{filepath}'"
            max_count = os.path.getsize(filepath)
            c = SpeedCounter(max_count=max_count, header=header)
    else:
        filepath = None
        buf = filepath_or_buffer
        if progress:
            from lpu.common.progress import SpeedCounter
            header = "loading buffer"
            c = SpeedCounter(header=header)
    #data = io.BytesIO()
    #f_in = _open(filename, 'rb')
    #    header = "loading file '%(filename)s'" % locals()
    #    max_count = os.path.getsize(filename)
    while True:
        #buf = f_in.read(bs)
        data = buf.read(bs)
        if not data:
            break
        else:
            #data.write(buf)
            out_buffer.write(data)
            if progress:
                #c.set_count(data.tell(), True)
                c.set_count(out_buffer.tell(), True)
    buf.close()
    #data.seek(0)
    out_buffer.seek(0)
    if progress:
        c.reset()
    if isinstance(filepath, str) and get_ext(filepath) == '.gz':
        #f_in = gzip.GzipFile(fileobj = data)
        #f_in.myfileobj = data
        fobj = gzip.GzipFile(fileobj = out_buffer)
        # typeshed declares myfileobj as FileIO | None; non-FileIO buffers
        # such as BytesIO work fine at runtime.
        # (typeshed 上の myfileobj は FileIO | None だが、BytesIO のような
        #  非 FileIO のバッファも実行時には問題なく動作する)
        fobj.myfileobj = out_buffer  # type: ignore[assignment]
        return fobj
    else:
        return out_buffer

def load_to_buffer(
    filepath_or_buffer: str | Any,
    progress: bool = True,
    bs: int = DEFAULT_BUFFER_SIZE,
) -> io.IOBase:
    #data = io.BytesIO()
    return load(filepath_or_buffer, io.BytesIO(), progress, bs)

def load_to_temp(
    filepath_or_buffer: str | Any,
    progress: bool = True,
    bs: int = DEFAULT_BUFFER_SIZE,
    named: bool = True,
) -> Any:
    # NamedTemporaryFile exposes the real file object as `.file`, while
    # TemporaryFile is the file object itself; typeshed's IO[bytes] return
    # types hide both, so they are treated as Any here.
    # (NamedTemporaryFile は実際のファイルを .file に持ち、TemporaryFile は
    #  自身がファイルオブジェクト。typeshed の IO[bytes] ではどちらも
    #  見えないため Any として扱う)
    temp: Any
    if named:
        temp = tempfile.NamedTemporaryFile()
        load(filepath_or_buffer, temp.file, progress, bs)
    else:
        temp = tempfile.TemporaryFile()
        load(filepath_or_buffer, temp, progress, bs)
    return temp

def safeMakeDirs(dirpath: str, **options: Any) -> None:
    '''make directories recursively for given path, don't throw exception if directory exists but if file exists'''
    if not os.path.isdir(dirpath):
        logger.debug(f'making directory: "{dirpath}"')
        try:
            os.makedirs(dirpath, **options)
        except OSError:
            logger.debug(f'cannot make directory: "{dirpath}"')

def open(filename: str, mode: str = 'r') -> io.IOBase:
    '''open the plain/compressed file transparently'''
    # gzip.open / io.open have unrelated typeshed classes, so the holder is
    # typed as Any.
    # (gzip.open と _open の typeshed 上の型が異なるため Any で受ける)
    file_obj: Any
    if get_ext(filename) == '.gz':
        file_obj = gzip.open(filename, mode)
    elif mode.find('r') >= 0 and is_gzipped(filename):
        file_obj = gzip.open(filename, mode)
    else:
        #logger.debug("normal open mode")
        if mode.find('t') >= 0 and sys.version_info[0] >= 3:
            #file_obj = _open(filename, mode, encoding='utf-8', errors='replace')
            file_obj = _open(filename, mode, encoding='utf-8', errors='backslashreplace')
        else:
            file_obj = _open(filename, mode)
    return file_obj

def rawfile(f: Any) -> io.IOBase:
    if hasattr(f, 'myfileobj'):
        # for archive files such as gzip
        return f.myfileobj
#    if isinstance(f, gzip.GzipFile):
    elif hasattr(f, 'buffer'):
        # for buffered files such as utf-8 mode
        #return f.buffer
        # might be duplicated buffer
        return rawfile(f.buffer)
    #elif isIOType(f):
    elif isinstance(f, FileType):
        return f
    else:
        logger.debug(f)
        #logging.debug(type(f))
        #logging.debug(dir(f))
        # python -O では assert 文が消えるため、明示的に送出する
        raise AssertionError(f'unsupported file object: {type(f)}')

def rawsize(f: Any) -> int:
    try:
        raw = rawfile(f)
        pos = raw.tell()
        # seek(-1, 2) points one byte before the end of the file, which
        # made the reported size one byte too small.
        # seek(-1, 2) ではファイル末尾の 1 バイト手前を指すため
        # サイズが 1 バイト少なくなっていた
        raw.seek(0, 2)
        size = raw.tell()
        raw.seek(pos, 0)
        return size
    except Exception as e:
        logger.debug(repr(e))
        return -1

def rawremain(f: Any) -> int:
    return rawsize(f) - rawtell(f)

def rawtell(fileobj: Any) -> int:
    '''get the current position of the opend file, return raw (not expanded) position for compressed'''
    return rawfile(fileobj).tell()

def testFile(path: str) -> bool:
    '''test file existence'''
    if os.path.isfile(path):
        return True
    #logger.debug("file does not exist: '%s'" % path)
    raise FileNotFoundError(f"file does not exist: '{path}'")

def wait_file(
    filepath: str,
    interval: float = 1,
    timeout: float = 0,
    delay: float = 0,
    quiet: bool = False,
) -> bool:
    if interval < 0:
        interval = 1
    if delay > 0:
        time.sleep(delay)
    if not os.path.exists(filepath):
        if not quiet:
            logger.info(f"waiting for file: {filepath}")
        start = time.time()
    while not os.path.exists(filepath):
        time.sleep(interval)
        elapsed = time.time() - start
        if timeout > 0 and elapsed > timeout:
            if not quiet:
                logger.error(f"waiting file ({filepath}) was timed out ({timeout} seconds)")
            return False
    if not quiet:
        logger.info(f"file exists: {filepath}")
    return True

def wait_files(
    filepaths: str | Iterable[str],
    interval: float = 1,
    timeout: float = 0,
    delay: float = 0,
    quiet: bool = False,
) -> None:
    if isinstance(filepaths, str):
        filepaths = [filepaths]
    for path in filepaths:
        wait_file(path, interval, timeout, delay, quiet)

