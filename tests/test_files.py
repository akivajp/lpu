# -*- coding: utf-8 -*-

'''Tests for lpu.common.files

lpu.common.files のテスト。
'''

import gzip
import io
import os

import pytest

from lpu.common import files


@pytest.fixture
def corpus_text():
    '''A body large enough that gzip actually compresses it

    gzip が実際に圧縮されるだけの分量の本文。
    '''
    return ''.join('line%d\n' % i for i in range(1000))


@pytest.fixture
def gz_path(tmp_path, corpus_text):
    # Written as bytes so that the content is identical on every platform
    # (text mode would translate "\n" into "\r\n" on Windows).
    # どのプラットフォームでも内容が同一になるようバイトで書き出す
    # (テキストモードでは Windows で "\n" が "\r\n" に変換される)。
    path = tmp_path / 'corpus.txt.gz'
    with gzip.open(str(path), 'wb') as f:
        f.write(corpus_text.encode('utf-8'))
    return path


@pytest.fixture
def plain_path(tmp_path, corpus_text):
    path = tmp_path / 'corpus.txt'
    path.write_bytes(corpus_text.encode('utf-8'))
    return path


class TestIsGzipped:
    def test_detects_gzip(self, gz_path):
        assert files.is_gzipped(str(gz_path))

    def test_rejects_plain_text(self, plain_path):
        assert not files.is_gzipped(str(plain_path))

    def test_rejects_missing_file(self, tmp_path):
        assert not files.is_gzipped(str(tmp_path / 'missing'))


class TestOpen:
    '''Transparent access to gzip files / gzip ファイルの透過アクセス'''

    def test_reads_gzip_transparently(self, gz_path, corpus_text):
        with files.open(str(gz_path), 'rt') as f:
            assert f.read() == corpus_text

    def test_reads_gzip_as_bytes(self, gz_path, corpus_text):
        with files.open(str(gz_path), 'rb') as f:
            assert f.read() == corpus_text.encode('utf-8')

    def test_reads_plain_text(self, plain_path, corpus_text):
        with files.open(str(plain_path), 'rt') as f:
            assert f.read() == corpus_text

    def test_writes_gzip_by_extension(self, tmp_path):
        path = tmp_path / 'out.gz'
        with files.open(str(path), 'wt') as f:
            f.write('hello\n')
        # The result must be readable as gzip / gzip として読めること
        with gzip.open(str(path), 'rt') as f:
            assert f.read() == 'hello\n'

    def test_detects_gzip_by_magic_number(self, tmp_path, gz_path,
                                          corpus_text):
        # a gzip file whose name does not end with .gz is still opened
        # transparently by checking the magic number
        # (拡張子が .gz でなくてもマジックナンバーにより
        #  透過的に gzip として開かれる)
        renamed = tmp_path / 'corpus.bin'
        renamed.write_bytes(gz_path.read_bytes())
        with files.open(str(renamed)) as f_in:
            # without a text mode flag the transparent open returns bytes
            # (テキストモード指定が無い場合、透過オープンはバイト列を返す)
            assert f_in.read() == corpus_text.encode('utf-8')


class TestGetContentSize:
    '''Regression tests for the uncompressed size / 展開後サイズの回帰テスト'''

    def test_returns_uncompressed_size_for_gzip(self, gz_path, corpus_text):
        '''The uncompressed size is read from the gzip ISIZE trailer

        0.2.x used gzip.read32(), which no longer exists, so this always
        returned -1 and silently disabled progress reporting over gzip.

        gzip の ISIZE フィールドから展開後サイズを読むこと。
        0.2.x は既に存在しない gzip.read32() を使っていたため常に -1 を返し、
        gzip に対する進捗表示が無言で無効化されていた。
        '''
        assert files.getContentSize(str(gz_path)) == len(corpus_text)

    def test_returns_file_size_for_plain_text(self, plain_path):
        expected = os.path.getsize(str(plain_path))
        assert files.getContentSize(str(plain_path)) == expected

    def test_returns_minus_one_for_missing_file(self, tmp_path):
        assert files.getContentSize(str(tmp_path / 'missing')) == -1


class TestRawSize:
    def test_returns_the_compressed_file_size(self, gz_path):
        '''rawsize reports the size on disk, not the expanded size

        0.2.x used seek(-1, 2) and was one byte short.

        rawsize は展開後ではなくディスク上のサイズを返すこと。
        0.2.x は seek(-1, 2) を使っており 1 バイト少なかった。
        '''
        expected = os.path.getsize(str(gz_path))
        f = files.open(str(gz_path), 'rb')
        try:
            assert files.rawsize(f) == expected
        finally:
            f.close()

    def test_does_not_disturb_the_read_position(self, plain_path):
        f = files.open(str(plain_path), 'rb')
        try:
            f.read(10)
            position = f.tell()
            files.rawsize(f)
            assert f.tell() == position
        finally:
            f.close()


class TestMisc:
    def test_get_ext(self):
        assert files.get_ext('a/b/c.txt') == '.txt'
        assert files.get_ext('a/b/c') == ''

    def test_test_file_raises_for_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            files.testFile(str(tmp_path / 'missing'))

    def test_safe_make_dirs_is_idempotent(self, tmp_path):
        target = str(tmp_path / 'x' / 'y')
        files.safeMakeDirs(target)
        files.safeMakeDirs(target)
        assert os.path.isdir(target)

    def test_concat_into_expands_compressed_inputs(self, tmp_path, gz_path,
                                                   plain_path, corpus_text):
        out = tmp_path / 'merged.txt'
        files.concat_into([str(gz_path), str(plain_path)], str(out),
                          progress=False)
        assert out.read_text(encoding='utf-8') == corpus_text * 2

    def test_wait_file_returns_true_for_existing_file(self, plain_path):
        assert files.wait_file(str(plain_path), quiet=True)

    def test_wait_file_times_out(self, tmp_path):
        missing = str(tmp_path / 'missing')
        assert not files.wait_file(missing, interval=1, timeout=1, quiet=True)


class TestConcatInto:
    def test_accepts_a_single_path_string(self, tmp_path, plain_path,
                                          corpus_text):
        out = tmp_path / 'single.txt'
        files.concat_into(str(plain_path), str(out), progress=False)
        assert out.read_text(encoding='utf-8') == corpus_text

    def test_shows_progress(self, tmp_path, gz_path, plain_path,
                            corpus_text):
        out = tmp_path / 'merged_progress.txt'
        files.concat_into([str(gz_path), str(plain_path)], str(out),
                          progress=True)
        assert out.read_text(encoding='utf-8') == corpus_text * 2


class TestCastFile:
    def test_returns_the_given_file_object_itself(self, plain_path):
        with open(str(plain_path), encoding='utf-8') as f_in:
            assert files.castFile(f_in) is f_in

    def test_opens_a_path_string(self, plain_path, corpus_text):
        f_in = files.castFile(str(plain_path))
        try:
            assert f_in.read() == corpus_text
        finally:
            f_in.close()


class TestIsMode:
    def test_text_file_modes(self, plain_path):
        with open(str(plain_path), encoding='utf-8') as f_in:
            assert files.is_mode(f_in, 'r')
            assert files.is_mode(f_in, 'read')
            assert not files.is_mode(f_in, 'w')
            assert not files.is_mode(f_in, 'b')
            assert files.is_mode(f_in, 't')

    def test_binary_file_modes(self, gz_path):
        with files.open(str(gz_path)) as f_in:
            # GzipFile keeps a .mode attribute ('rb')
            # (GzipFile は .mode 属性に 'rb' を持つ)
            assert files.is_mode(f_in, 'b')
            assert not files.is_mode(f_in, 't')

    def test_unknown_mode_returns_none(self, plain_path):
        with open(str(plain_path), encoding='utf-8') as f_in:
            assert files.is_mode(f_in, 'x') is None


class TestLoad:
    def test_loads_a_plain_file_into_a_buffer(self, plain_path, corpus_text):
        out = io.BytesIO()
        result = files.load(str(plain_path), out, progress=False)
        assert result is out
        assert out.tell() == 0
        assert out.read() == corpus_text.encode('utf-8')

    def test_loads_from_a_file_object(self, plain_path, corpus_text):
        with open(str(plain_path), 'rb') as f_in:
            out = files.load(f_in, io.BytesIO(), progress=False)
        assert out.read() == corpus_text.encode('utf-8')

    def test_expands_a_gzip_file(self, gz_path, corpus_text):
        out = io.BytesIO()
        result = files.load(str(gz_path), out, progress=False)
        assert isinstance(result, gzip.GzipFile)
        assert result.myfileobj is out
        assert result.read() == corpus_text.encode('utf-8')

    def test_load_to_buffer(self, plain_path, corpus_text, gz_path):
        buf = files.load_to_buffer(str(plain_path), progress=False)
        assert buf.read() == corpus_text.encode('utf-8')
        buf = files.load_to_buffer(str(gz_path), progress=False)
        assert isinstance(buf, gzip.GzipFile)
        assert buf.read() == corpus_text.encode('utf-8')

    def test_load_to_temp_named(self, plain_path, corpus_text):
        temp = files.load_to_temp(str(plain_path), progress=False)
        try:
            assert temp.read() == corpus_text.encode('utf-8')
        finally:
            temp.close()

    def test_load_to_temp_unnamed(self, plain_path, corpus_text):
        temp = files.load_to_temp(str(plain_path), progress=False,
                                  named=False)
        try:
            assert temp.read() == corpus_text.encode('utf-8')
        finally:
            temp.close()

    def test_load_with_progress(self, plain_path, corpus_text):
        out = io.BytesIO()
        files.load(str(plain_path), out, progress=True)
        assert out.read() == corpus_text.encode('utf-8')


class TestRawPosition:
    def test_rawfile_of_gzip_returns_the_underlying_file(self, gz_path):
        with files.open(str(gz_path)) as f_in:
            raw = files.rawfile(f_in)
            # gzip.open() opens the file through the builtins, so the raw
            # stream of a GzipFile is its BufferedReader
            # (gzip.open() は組み込みの open 経由で開くため、GzipFile の
            #  raw ストリームは BufferedReader になる)
            assert raw is f_in.myfileobj
            assert isinstance(raw, io.BufferedReader)

    def test_rawfile_of_a_text_file_returns_the_binary_stream(
            self, plain_path):
        with open(str(plain_path), encoding='utf-8') as f_in:
            raw = files.rawfile(f_in)
            # the .buffer chain of a TextIOWrapper ends at its BufferedReader
            # (TextIOWrapper の .buffer 辿りの終点は BufferedReader)
            assert isinstance(raw, io.BufferedReader)

    def test_rawsize_returns_minus_one_for_unsupported_objects(self):
        # a plain object without a .buffer chain and no IOBase interface
        # raises inside rawfile, which is caught and reported as -1
        # (myfileobj / buffer / IOBase のいずれでも無いオブジェクトは
        #  rawfile 内で例外となり、rawsize は -1 を返す)
        assert files.rawsize(object()) == -1

    def test_rawtell_tracks_the_raw_position(self, plain_path):
        size = os.path.getsize(str(plain_path))
        with files.open(str(plain_path), 'rb') as f_in:
            assert files.rawtell(f_in) == 0
            assert files.rawremain(f_in) == size
            f_in.read(10)
            assert files.rawtell(f_in) == 10
            assert files.rawremain(f_in) == size - 10


class TestSafeMakeDirs:
    def test_does_not_raise_when_a_file_exists(self, tmp_path):
        conflict = tmp_path / 'conflict'
        conflict.write_text('x')
        files.safeMakeDirs(str(conflict))
        assert conflict.is_file()


class TestWaitFiles:
    def test_treats_a_negative_interval_as_one(self, plain_path):
        assert files.wait_file(str(plain_path), interval=-1, quiet=True)

    def test_accepts_a_single_path_string(self, plain_path):
        files.wait_files(str(plain_path), interval=1, quiet=True)

    def test_accepts_a_list_of_paths(self, tmp_path):
        paths = []
        for i in range(2):
            path = tmp_path / ('file%d' % i)
            path.write_text('x')
            paths.append(str(path))
        files.wait_files(paths, interval=1, quiet=True)
