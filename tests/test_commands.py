# -*- coding: utf-8 -*-

'''Tests for the command line entry points

Each command is invoked in a subprocess through its main() function, so
that the tests work both from an installed package and from an uncompiled
source checkout.

コマンドラインのエントリポイントのテスト。
インストール済みパッケージでも未コンパイルのソースツリーでも動くよう、
各コマンドを main() 経由で別プロセスとして起動する。
'''

import os
import subprocess
import sys

import pytest

from conftest import requires_smt
from conftest import requires_trans_models


def run_command(module, args, cwd=None, input_bytes=None, entry='main'):
    '''Invoke a command module's entry function in a subprocess

    コマンドモジュールのエントリ関数を別プロセスで起動する。

    Args:
        module: Module path, e.g. "lpu.commands.abspath". モジュールパス。
        args: Command line arguments. コマンドライン引数。
        cwd: Working directory. 作業ディレクトリ。
        input_bytes: Data to feed to stdin. 標準入力に渡すデータ。
        entry: Name of the entry function. エントリ関数名。

    Returns:
        The CompletedProcess. 実行結果。
    '''
    code = (
        'import sys;'
        'sys.argv = [%r] + sys.argv[1:];'
        'from %s import %s;'
        '%s()' % (module.rsplit('.', 1)[-1], module, entry, entry)
    )
    return subprocess.run(
        [sys.executable, '-c', code] + list(args),
        cwd=cwd, input=input_bytes, capture_output=True,
    )


# Commands that need no compiled extension / コンパイル拡張が不要なコマンド
PURE_COMMANDS = [
    'lpu.commands.abspath',
    'lpu.commands.clean_parallel',
    'lpu.commands.dialog',
    'lpu.commands.exec_parallel',
    'lpu.commands.guess_langcode',
    'lpu.commands.progress',
    'lpu.commands.random_split',
    'lpu.commands.wait_files',
]

# Phrase/rule table tools, registered as entry points in 0.3.0
# 0.3.0 で entry point に登録したフレーズ/ルールテーブル操作ツール
TRANS_MODELS_COMMANDS = [
    'lpu.smt.trans_models.convert_extract',
    'lpu.smt.trans_models.filter',
    'lpu.smt.trans_models.make_glue_rules',
    'lpu.smt.trans_models.normalize',
    'lpu.smt.trans_models.triangulate',
]

# Word alignment entry points / 単語アライメントのエントリポイント
SMT_ALIGN_ENTRIES = ['main_train', 'main_score']


@pytest.mark.parametrize('module', PURE_COMMANDS)
def test_every_command_provides_help(module):
    '''--help must succeed for every command

    全コマンドが --help に成功すること。
    '''
    result = run_command(module, ['--help'])
    assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
    assert b'usage' in result.stdout.lower()


@requires_trans_models
@pytest.mark.parametrize('module', TRANS_MODELS_COMMANDS)
def test_every_trans_models_command_provides_help(module):
    '''The newly registered SMT tools must be reachable and offer --help

    0.3.0 で登録した SMT ツールが到達可能で --help を提供すること。
    '''
    result = run_command(module, ['--help'])
    assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
    assert b'usage' in result.stdout.lower()


@requires_smt
@pytest.mark.parametrize('entry', SMT_ALIGN_ENTRIES)
def test_word_align_commands_provide_help(entry):
    result = run_command('lpu.smt.align.ibm_models', ['--help'], entry=entry)
    assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
    assert b'usage' in result.stdout.lower()


class TestAbspath:
    def test_prints_the_absolute_path(self, tmp_path):
        target = tmp_path / 'file.txt'
        target.write_text('x', encoding='utf-8')
        result = run_command('lpu.commands.abspath', ['file.txt'],
                             cwd=str(tmp_path))
        assert result.returncode == 0
        assert result.stdout.decode().strip() == str(target)


class TestGuessLangcode:
    def test_guesses_from_the_file_name(self):
        result = run_command('lpu.commands.guess_langcode',
                             ['corpus.en.txt', 'corpus.fr.txt'])
        assert result.stdout.decode().strip() == 'en fr'

    def test_reports_unknown_without_a_language_field(self):
        result = run_command('lpu.commands.guess_langcode', ['corpus.txt'])
        assert result.stdout.decode().strip() == 'UNK'


class TestProgress:
    def test_passes_stdin_through_to_stdout(self):
        payload = b''.join(b'%d\n' % i for i in range(100))
        result = run_command('lpu.commands.progress', ['--lines'],
                             input_bytes=payload)
        assert result.returncode == 0
        assert result.stdout == payload


class TestExecParallel:
    def test_runs_a_command_over_split_chunks(self, tmp_path):
        '''The output must equal the result of running the command once

        分割実行の結果が一括実行の結果と一致すること。
        '''
        source = tmp_path / 'input.txt'
        source.write_text('alpha\nbeta\ngamma\ndelta\n', encoding='utf-8')
        output = tmp_path / 'output.txt'
        result = run_command('lpu.commands.exec_parallel', [
            '--input', str(source), '--output', str(output),
            '--threads', '2', '--chunks', '2', 'tr a-z A-Z',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert output.read_text(encoding='utf-8') == 'ALPHA\nBETA\nGAMMA\nDELTA\n'


class TestRandomSplit:
    def test_keeps_parallel_lines_aligned(self, tmp_path):
        '''Splitting a parallel corpus must preserve line correspondence

        対訳コーパスの分割で行の対応が保たれること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        pairs = [('en%d' % i, 'fr%d' % i) for i in range(10)]
        src.write_text(''.join('%s\n' % a for a, _ in pairs), encoding='utf-8')
        trg.write_text(''.join('%s\n' % b for _, b in pairs), encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src), str(trg),
            '--suffixes', 'en', 'fr',
            '--tags', 'train', 'test',
            '--split-sizes', '7', '3',
            '--random-seed', '42', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')

        expected = dict(pairs)
        total = 0
        for tag, size in [('train', 7), ('test', 3)]:
            en_lines = (tmp_path / ('%s.en' % tag)).read_text(
                encoding='utf-8').split()
            fr_lines = (tmp_path / ('%s.fr' % tag)).read_text(
                encoding='utf-8').split()
            assert len(en_lines) == size
            assert len(fr_lines) == size
            for en_line, fr_line in zip(en_lines, fr_lines):
                assert expected[en_line] == fr_line
            total += size
        assert total == len(pairs)


class TestCleanParallel:
    def test_drops_empty_lines_from_both_sides(self, tmp_path):
        src = tmp_path / 'corpus.en.txt'
        trg = tmp_path / 'corpus.fr.txt'
        src.write_text('a b\n\nc d\n', encoding='utf-8')
        trg.write_text('x y\n\nz w\n', encoding='utf-8')
        result = run_command('lpu.commands.clean_parallel', [
            '--min', '1', '--max', '10', str(src), str(trg), 'cleaned',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        en_lines = (tmp_path / 'corpus.en.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        fr_lines = (tmp_path / 'corpus.fr.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        assert en_lines == ['a b', 'c d']
        assert fr_lines == ['x y', 'z w']


class TestWaitFiles:
    def test_returns_immediately_for_an_existing_file(self, tmp_path):
        target = tmp_path / 'exists.txt'
        target.write_text('x', encoding='utf-8')
        result = run_command('lpu.commands.wait_files',
                             ['--quiet', str(target)])
        assert result.returncode == 0

    def test_times_out_for_a_missing_file(self, tmp_path):
        missing = tmp_path / 'missing.txt'
        result = run_command('lpu.commands.wait_files', [
            '--quiet', '--interval', '1', '--timeout', '1', str(missing),
        ])
        # The command must terminate rather than wait forever
        # 無限に待たずに終了すること
        assert result.returncode is not None


@requires_smt
class TestWordAlign:
    '''End-to-end training and scoring of the IBM models

    IBM モデルの学習とスコアリングの end-to-end テスト。
    '''

    def test_train_learns_the_expected_alignment(self, tmp_path,
                                                 parallel_corpus):
        src_path, trg_path = parallel_corpus
        trans_path = tmp_path / 'trans.txt'
        align_path = tmp_path / 'align.txt'
        result = run_command('lpu.smt.align.ibm_models', [
            '--iteration-limit', '10', '--quiet',
            str(src_path), str(trg_path), str(trans_path), str(align_path),
        ], cwd=str(tmp_path), entry='main_train')
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')

        # Collect the most probable translation of each source word
        # 各原言語単語について最も確率の高い訳語を取り出す
        best = {}
        for line in trans_path.read_text(encoding='utf-8').splitlines():
            fields = line.split('\t')
            if len(fields) < 3:
                continue
            source, target, probability = fields[0], fields[1], float(fields[2])
            if source not in best or probability > best[source][1]:
                best[source] = (target, probability)

        expected = {
            'the': 'le', 'cat': 'chat', 'dog': 'chien',
            'sat': 'assis', 'ran': 'couru', 'a': 'un',
        }
        for source, target in expected.items():
            assert source in best, 'missing source word: %s' % source
            assert best[source][0] == target, (
                'expected %s -> %s, got %s' % (source, target, best[source][0]))

    def test_score_requires_an_output_option(self, tmp_path, parallel_corpus):
        src_path, trg_path = parallel_corpus
        trans_path = tmp_path / 'trans.txt'
        trans_path.write_text('the\tle\t1.0\t1.0\n', encoding='utf-8')
        result = run_command('lpu.smt.align.ibm_models', [
            str(src_path), str(trg_path), str(trans_path),
        ], cwd=str(tmp_path), entry='main_score')
        # Without --save-scores or --decode-align the command must not
        # silently produce nothing
        # --save-scores も --decode-align も無い場合は無言で終わらないこと
        output = (result.stdout + result.stderr).decode('utf-8', 'replace')
        assert 'necessary' in output or result.returncode != 0
