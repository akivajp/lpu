#!/usr/bin/env python

'''Auxiliary functions for file I/O'''

from __future__ import annotations

# Standard libraries
import glob
import gzip
import io
import os.path
import shutil
import sys
import tempfile
import time
from collections.abc import Iterable
from typing import Any, cast

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
        return cast(io.IOBase, anyFile)
    else:
        return cast(io.IOBase, open(anyFile))

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
    _, ext = os.path.splitext(filename)
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
        return bool(fmode.find('r') >= 0)
    elif mode in ('w', 'write'):
        return bool(fmode.find('w') >= 0)
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

# The safe_* helpers below share one contract: a missing source is not an
# error (they report it by returning False / 0), while any other OSError
# propagates to the caller. Swallowing every exception would turn a
# permission problem into silent data loss.
# 以下の safe_* 群は共通の規約を持つ: コピー元/削除対象が存在しないことは
# エラーとせず戻り値 (False / 0) で伝え、それ以外の OSError は呼び出し側へ
# 送出する。全例外を握り潰すと権限エラーが静かなデータ欠損に化けるため。

def safe_remove(path: str, log: bool = True) -> int:
    """remove the file at given path, ignoring its absence

    指定パスのファイルを削除する。存在しない場合は何もしない。

    If the path contains a wildcard (``*``), every matching file is removed.
    パスにワイルドカード (``*``) を含む場合、一致する全ファイルを削除する。

    Args:
        path: The path (or glob pattern) of the file(s) to remove.
            削除するファイルのパス (または glob パターン)。
        log: Whether to write a debug log for each removal.
            削除ごとにデバッグログを出力するかどうか。

    Returns:
        The number of files actually removed.
            実際に削除できたファイル数。
    """
    # ワイルドカードを含む場合は展開し、各実体を再帰的に処理する
    if '*' in path:
        removed = 0
        for matched in glob.glob(path):
            removed += safe_remove(matched, log=log)
        return removed
    try:
        os.remove(path)
    except FileNotFoundError:
        # 既に存在しないのは想定内 (削除済みと同じ結果なので成功扱いしない)
        return 0
    if log:
        logger.debug(f'removed file: "{path}"')
    return 1

def safe_copy(src: str, dst: str, log: bool = True) -> bool:
    """copy a file over the destination, replacing it if it exists

    ファイルをコピーする。コピー先が既に存在する場合は置き換える。

    Args:
        src: The path of the source file.
            コピー元ファイルのパス。
        dst: The path of the destination file.
            コピー先ファイルのパス。
        log: Whether to write a debug log for the copy.
            コピー時にデバッグログを出力するかどうか。

    Returns:
        True if the copy was made, False if the source does not exist.
            コピーを行えたら True、コピー元が存在しなければ False。
    """
    if not os.path.exists(src):
        return False
    # copy2 は既存ファイルを上書きするが、コピー先がシンボリックリンクだと
    # リンク先を書き換えてしまうため、先に削除して実体を切り離す
    safe_remove(dst, log=False)
    if log:
        logger.debug(f'copying file: "{src}" -> "{dst}"')
    shutil.copy2(src, dst)
    return True

def safe_link(src: str, dst: str, log: bool = True) -> bool:
    """link a file at the destination, falling back to a symbolic link

    ファイルへのリンクを作成する。ハードリンクを作れない場合は
    シンボリックリンクにフォールバックする。

    A hard link cannot cross filesystems and is unavailable on some
    filesystems, so a failure falls back to a symbolic link rather than
    propagating.
    ハードリンクはファイルシステムを跨げず、一部のファイルシステムでは
    利用できないため、失敗時は送出せずシンボリックリンクに切り替える。

    Args:
        src: The path of the source file.
            リンク元ファイルのパス。
        dst: The path of the link to create.
            作成するリンクのパス。
        log: Whether to write a debug log for the link.
            リンク作成時にデバッグログを出力するかどうか。

    Returns:
        True if a link was created, False if the source does not exist.
            リンクを作成できたら True、リンク元が存在しなければ False。
    """
    if not os.path.exists(src):
        return False
    safe_remove(dst, log=False)
    try:
        os.link(src, dst)
    except OSError:
        # ファイルシステムを跨ぐ場合などはハードリンクを作れないため、
        # シンボリックリンクで代替する (これも失敗すれば送出する)
        os.symlink(src, dst)
        if log:
            logger.debug(f'made symbolic link: "{src}" -> "{dst}"')
        return True
    if log:
        logger.debug(f'made hard link: "{src}" -> "{dst}"')
    return True

def safe_rename(src: str, dst: str, log: bool = True) -> bool:
    """rename a file over the destination, replacing it if it exists

    ファイルを改名する。改名先が既に存在する場合は置き換える。

    `os.replace` is used rather than `os.rename` so that an existing
    destination is replaced atomically on every supported platform
    (`os.rename` raises on Windows when the destination exists).
    `os.rename` ではなく `os.replace` を用いる。これは対応する全
    プラットフォームで既存の改名先を原子的に置き換えるため
    (`os.rename` は Windows で改名先が存在すると例外を送出する)。

    Args:
        src: The path of the file to rename.
            改名するファイルのパス。
        dst: The new path of the file.
            改名後のファイルのパス。
        log: Whether to write a debug log for the rename.
            改名時にデバッグログを出力するかどうか。

    Returns:
        True if the file was renamed, False if the source does not exist.
            改名できたら True、改名元が存在しなければ False。
    """
    if not os.path.exists(src):
        return False
    if log:
        logger.debug(f'renaming file: "{src}" -> "{dst}"')
    os.replace(src, dst)
    return True

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
    return cast(io.IOBase, file_obj)

def rawfile(f: Any) -> io.IOBase:
    if hasattr(f, 'myfileobj'):
        # for archive files such as gzip
        return cast(io.IOBase, f.myfileobj)
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

