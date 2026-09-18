
'''Shared fixtures and skip conditions for the test suite

テストスイート共通のフィクスチャとスキップ条件。
'''

import importlib

import pytest


def _module_available(name):
    '''Report whether a module can be imported

    モジュールが import 可能かどうかを返す。
    '''
    try:
        importlib.import_module(name)
    except Exception:
        return False
    return True


# The Cython extensions are unavailable in an uncompiled source checkout, and
# lpu.data_structs.trie additionally requires the pycedar package.
# 未コンパイルのソースツリーでは Cython 拡張が利用できず、
# lpu.data_structs.trie はさらに pycedar パッケージを必要とする。
requires_trie = pytest.mark.skipif(
    not _module_available('lpu.data_structs.trie'),
    reason='lpu.data_structs.trie requires the compiled extension and pycedar',
)

requires_smt = pytest.mark.skipif(
    not _module_available('lpu.smt.align.ibm_models'),
    reason='lpu.smt.align.ibm_models requires the compiled extension and numpy',
)

# The phrase/rule table tools build on the compiled records/tables modules.
# フレーズ/ルールテーブル操作ツールはコンパイル済みの records/tables に依存する。
requires_trans_models = pytest.mark.skipif(
    not _module_available('lpu.smt.trans_models.tables'),
    reason='lpu.smt.trans_models requires the compiled extension and pycedar',
)


@pytest.fixture
def parallel_corpus(tmp_path):
    '''Create a tiny word-aligned parallel corpus and return both paths

    単語対応が明らかな極小の対訳コーパスを作成し、両方のパスを返す。
    '''
    src_path = tmp_path / 'src.txt'
    trg_path = tmp_path / 'trg.txt'
    # Written as bytes to keep LF line endings on every platform
    # どのプラットフォームでも LF 改行を保つためバイトで書き出す
    src_path.write_bytes(b'the cat sat\nthe dog ran\nthe cat ran\na dog sat\n')
    trg_path.write_bytes(
        b'le chat assis\nle chien couru\nle chat couru\nun chien assis\n')
    return src_path, trg_path


@pytest.fixture
def crlf_parallel_corpus(tmp_path):
    '''The same corpus with CRLF line endings

    CRLF 改行の同じコーパス。
    '''
    src_path = tmp_path / 'src_crlf.txt'
    trg_path = tmp_path / 'trg_crlf.txt'
    src_path.write_bytes(
        b'the cat sat\r\nthe dog ran\r\nthe cat ran\r\na dog sat\r\n')
    trg_path.write_bytes(
        b'le chat assis\r\nle chien couru\r\nle chat couru\r\n'
        b'un chien assis\r\n')
    return src_path, trg_path
