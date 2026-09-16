# -*- coding: utf-8 -*-

'''Tests for lpu.common.files

lpu.common.files のテスト。
'''

import gzip
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
    path = tmp_path / 'corpus.txt.gz'
    with gzip.open(str(path), 'wt') as f:
        f.write(corpus_text)
    return path


@pytest.fixture
def plain_path(tmp_path, corpus_text):
    path = tmp_path / 'corpus.txt'
    path.write_text(corpus_text, encoding='utf-8')
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
