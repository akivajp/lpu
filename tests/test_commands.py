
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
from pathlib import Path

import pytest

from conftest import requires_smt
from conftest import requires_trans_models

from lpu.commands import random_split
from lpu.commands.clean_parallel import cleanParallel
from lpu.common.config import Config


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
        'sys.argv = [{!r}] + sys.argv[1:];'
        'from {} import {};'
        '{}()'.format(module.rsplit('.', 1)[-1], module, entry, entry)
    )
    kwargs = {}
    # When pytest-cov (--cov) is measuring this process, make the child
    # measure itself too: point its auto-measurement hook at the coverage
    # config and pin the data file to the repository root, regardless of
    # the child's cwd. The config's parallel = true keeps the data files
    # distinct until pytest-cov combines them.
    # (pytest-cov (--cov) 計測中は子プロセスも自身を計測させる。自動計測
    #  フック用の設定ファイルを指し、データファイルを子の cwd にかかわらず
    #  リポジトリルートに固定する。設定の parallel = true により
    #  combine まで各データファイルが分離保存される。)
    if _cov_active():
        repo_root = Path(__file__).resolve().parent.parent
        kwargs['env'] = {
            **os.environ,
            'COVERAGE_PROCESS_START': str(repo_root / 'pyproject.toml'),
            'COVERAGE_FILE': str(repo_root / '.coverage'),
        }
    return subprocess.run(
        [sys.executable, '-c', code] + list(args),
        cwd=cwd, input=input_bytes, capture_output=True, **kwargs,
    )


def _cov_active():
    '''Report whether coverage measurement is running in this process

    自プロセスでカバレッジ計測が有効かどうかを返す (pytest-cov が --cov
    付きで起動している場合のみ真)。
    '''
    try:
        import coverage
    except ImportError:
        return False
    return coverage.Coverage.current() is not None


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

    def test_handles_a_partial_last_chunk(self, tmp_path):
        '''A chunk shorter than the split size stops at the file end

        最終チャンクが分割サイズに満たない場合、入力の終わりで
        書き出しを止めること。
        '''
        source = tmp_path / 'input.txt'
        # 5 lines over 2 chunks: the split size is 3, so the last chunk
        # is shorter and hits the end of the buffer
        # (5行を2分割。splitSize は3になり、最後のチャンクは
        #  バッファの終端に当たる)
        source.write_text('l1\nl2\nl3\nl4\nl5\n', encoding='utf-8')
        output = tmp_path / 'output.txt'
        result = run_command('lpu.commands.exec_parallel', [
            '--input', str(source), '--output', str(output),
            '--threads', '1', '--chunks', '2', '--interval', '0.01',
            'tr a-z A-Z',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert output.read_text(encoding='utf-8') == 'L1\nL2\nL3\nL4\nL5\n'

    def test_handles_an_empty_input(self, tmp_path):
        '''An empty input must finish cleanly with an empty output

        空の入力はエラーにならず、空の出力で終了すること。
        '''
        source = tmp_path / 'input.txt'
        source.write_text('', encoding='utf-8')
        output = tmp_path / 'output.txt'
        result = run_command('lpu.commands.exec_parallel', [
            '--input', str(source), '--output', str(output),
            '--threads', '2', '--chunks', '2', '--interval', '0.01',
            'tr a-z A-Z',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert output.read_text(encoding='utf-8') == ''

    def test_rejects_a_non_positive_chunk_count(self, tmp_path):
        '''--chunks 0 must abort instead of crashing on the split math

        --chunks 0 は分割サイズの計算でクラッシュする前に中断すること。
        '''
        source = tmp_path / 'input.txt'
        source.write_text('a\nb\n', encoding='utf-8')
        output = tmp_path / 'output.txt'
        result = run_command('lpu.commands.exec_parallel', [
            '--input', str(source), '--output', str(output),
            '--chunks', '0', 'tr a-z A-Z',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert b'should be positive integer' in result.stderr
        assert not output.exists()

    def test_skips_chunks_reported_by_another_worker(self, tmp_path):
        '''A chunk whose phase was taken over by another worker is skipped

        他のワーカーが完了報告済みのチャンクはスキップされ、
        その出力が連結されること。
        '''
        source = tmp_path / 'input.txt'
        source.write_text('ignored\n', encoding='utf-8')
        output = tmp_path / 'output.txt'
        workdir = tmp_path / 'wd'
        workdir.mkdir()
        # the phase files pretend another worker already finished chunk 1
        # (フェーズファイルにより、チャンク1を他のワーカーが完了した
        #  ことにする)
        (workdir / 'report.cmd.1.begin').write_text('other-host:1',
                                                    encoding='utf-8')
        (workdir / 'report.cmd.1.done').write_text('other-host:1',
                                                   encoding='utf-8')
        (workdir / 'split.1.out').write_text('PRE\n', encoding='utf-8')
        result = run_command('lpu.commands.exec_parallel', [
            '--input', str(source), '--output', str(output),
            '--tmpdir', str(workdir),
            '--threads', '1', '--chunks', '1', '--interval', '0.01',
            'tr a-z A-Z',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert output.read_text(encoding='utf-8') == 'PRE\n'

    def test_adopts_the_config_saved_by_another_splitter(self, tmp_path):
        '''When the split phase was taken over, its saved config is loaded

        分割フェーズを他のワーカーに譲った場合、保存済みの
        設定ファイルが採用されること。
        '''
        import json
        source = tmp_path / 'input.txt'
        source.write_text('ignored\n', encoding='utf-8')
        output = tmp_path / 'output.txt'
        workdir = tmp_path / 'wd'
        workdir.mkdir()
        (workdir / 'report.split.begin').write_text('other-host:1',
                                                    encoding='utf-8')
        (workdir / 'report.split.done').write_text('other-host:1',
                                                   encoding='utf-8')
        # the other worker already split the input into this chunk
        # (他のワーカーが既に入力をこのチャンクへ分割済み)
        (workdir / 'split.1.in').write_text('two\nlines\n', encoding='utf-8')
        config = {
            'numChunks': 1,
            'digits': 1,
            'lineCount': 2,
            'threads': 1,
            'interval': 0.01,
            'command': 'tr a-z A-Z',
        }
        (workdir / 'config.json').write_text(json.dumps(config),
                                             encoding='utf-8')
        result = run_command('lpu.commands.exec_parallel', [
            '--input', str(source), '--output', str(output),
            '--tmpdir', str(workdir),
            '--threads', '1', '--chunks', '1', '--interval', '0.01',
            'tr a-z A-Z',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert output.read_text(encoding='utf-8') == 'TWO\nLINES\n'

    def test_leaves_the_finalization_to_a_running_worker(self, tmp_path):
        '''When another worker is finalizing, this one just reports and exits

        連結フェーズを他のワーカーが実行中の場合、このプロセスは
        出力を書かずに終了すること。
        '''
        source = tmp_path / 'input.txt'
        source.write_text('a\nb\n', encoding='utf-8')
        output = tmp_path / 'output.txt'
        workdir = tmp_path / 'wd'
        workdir.mkdir()
        (workdir / 'report.concat.begin').write_text('other-host:1',
                                                     encoding='utf-8')
        (workdir / 'report.concat.done').write_text('other-host:1',
                                                    encoding='utf-8')
        result = run_command('lpu.commands.exec_parallel', [
            '--input', str(source), '--output', str(output),
            '--tmpdir', str(workdir),
            '--threads', '1', '--chunks', '1', '--interval', '0.01',
            'tr a-z A-Z',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        # the finalization belongs to the other worker, so nothing is
        # written to the output here
        # (連結は他のワーカーの担当のため、ここでは出力が書かれない)
        assert not output.exists()


class TestExecParallelHelpers:
    '''Unit tests for the module-level coordination helpers

    分散実行の調停を行うモジュールレベル関数のテスト。
    '''

    def test_report_writes_once_per_path(self, tmp_path):
        from lpu.commands import exec_parallel
        path = tmp_path / 'report.txt'
        assert exec_parallel.report(str(path), 'first') is True
        assert path.read_text(encoding='utf-8') == 'first'
        # an existing file is never overwritten
        # (既存のファイルは上書きされない)
        assert exec_parallel.report(str(path), 'second') is False
        assert path.read_text(encoding='utf-8') == 'first'

    def test_remove_accepts_a_path_string(self, tmp_path):
        from lpu.commands import exec_parallel
        path = tmp_path / 'buffer.txt'
        path.write_text('data', encoding='utf-8')
        exec_parallel.remove(str(path))
        assert not path.exists()

    def test_check_phase_reports_progression(self, tmp_path):
        from lpu.commands import exec_parallel
        from lpu.common.config import Config
        conf = Config(tmpdir=str(tmp_path))
        assert exec_parallel.checkPhase(conf, 'split') == 'none'
        (tmp_path / 'report.split.begin').write_text('worker',
                                                     encoding='utf-8')
        assert exec_parallel.checkPhase(conf, 'split') == 'started'
        (tmp_path / 'report.split.done').write_text('worker',
                                                    encoding='utf-8')
        # checkPhase() consults the begin file first, so the finished
        # state is only reported while the begin file is absent
        # (checkPhase() は begin ファイルを先に見るため、finished の
        #  判定は begin ファイルが無い場合にのみ行われる)
        (tmp_path / 'report.split.begin').unlink()
        assert exec_parallel.checkPhase(conf, 'split') == 'finished'

    def test_check_phase_charge_rejects_a_foreign_worker(self, tmp_path):
        from lpu.commands import exec_parallel
        from lpu.common.config import Config
        conf = Config(tmpdir=str(tmp_path))
        begin = tmp_path / 'report.split.begin'
        begin.write_text('other-host:1', encoding='utf-8')
        assert exec_parallel.checkPhaseCharge(conf, 'split') is False
        begin.write_text(exec_parallel.getCurrentWorkerID(),
                         encoding='utf-8')
        assert exec_parallel.checkPhaseCharge(conf, 'split') is True

    def test_int2str_zero_pads_the_file_number(self):
        from lpu.commands import exec_parallel
        assert exec_parallel.int2str(3, 3, '0') == '003'
        assert exec_parallel.int2str(123, 3, '0') == '123'


class TestExecParallelWorkerID:
    def test_worker_id_is_available_on_every_platform(self):
        '''getCurrentWorkerID must not depend on os.uname()

        0.2.x used os.uname(), which does not exist on Windows, so
        lpu-exec-parallel raised AttributeError there.

        getCurrentWorkerID が os.uname() に依存しないこと。
        0.2.x は Windows に存在しない os.uname() を使っていたため、
        lpu-exec-parallel がその環境で AttributeError になっていた。
        '''
        from lpu.commands.exec_parallel import getCurrentWorkerID
        worker_id = getCurrentWorkerID()
        assert ':' in worker_id
        host, pid = worker_id.rsplit(':', 1)
        assert host
        assert int(pid) == os.getpid()


class TestRandomSplit:
    def test_keeps_parallel_lines_aligned(self, tmp_path):
        '''Splitting a parallel corpus must preserve line correspondence

        対訳コーパスの分割で行の対応が保たれること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        pairs = [(f'en{i}', f'fr{i}') for i in range(10)]
        src.write_text(''.join(f'{a}\n' for a, _ in pairs), encoding='utf-8')
        trg.write_text(''.join(f'{b}\n' for _, b in pairs), encoding='utf-8')
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
            en_lines = (tmp_path / (f'{tag}.en')).read_text(
                encoding='utf-8').split()
            fr_lines = (tmp_path / (f'{tag}.fr')).read_text(
                encoding='utf-8').split()
            assert len(en_lines) == size
            assert len(fr_lines) == size
            # 直前で両側の行数一致を検証済み
            for en_line, fr_line in zip(en_lines, fr_lines, strict=True):
                assert expected[en_line] == fr_line
            total += size
        assert total == len(pairs)

    def test_writes_line_ids_with_the_ids_flag(self, tmp_path):
        '''--ids records the original (1-based) line numbers per tag

        --ids を付けると各タグの元の行番号 (1 起点) が出力されること。
        '''
        src = tmp_path / 'corpus.en'
        src.write_text(''.join(f'en{i}\n' for i in range(5)),
                       encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src),
            '--prefixes', 'out',
            '--suffixes', 'en',
            '--tags', 'a', 'b',
            '--split-sizes', '2', '3',
            '--random-seed', '7', '--ids', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        ids = []
        for tag in ['a', 'b']:
            # the prefix is concatenated without a separator
            # (prefix はセパレータ無しで結合される)
            lines = (tmp_path / (f'out{tag}.ids')).read_text(
                encoding='utf-8').split()
            assert len(lines) == (2 if tag == 'a' else 3)
            ids.extend(int(line) for line in lines)
        # every original line is reported exactly once
        # (全元行が正確に1回ずつ報告される)
        assert sorted(ids) == list(range(1, 6))

    def test_ignores_empty_lines_only_with_the_flag(self, tmp_path):
        '''--ignore-empty keeps the flag out of the split entirely

        --ignore-empty を付けると空行が分割から除外されること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        # line 1 is empty on both sides
        # (1行目は両側とも空行)
        src.write_text('en0\n\nen1\nen2\n', encoding='utf-8')
        trg.write_text('fr0\n\nfr1\nfr2\n', encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src), str(trg),
            '--suffixes', 'en', 'fr',
            '--tags', 'a', 'b',
            '--split-sizes', '3', '0',
            '--ignore-empty', '--random-seed', '1', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        en_lines = (tmp_path / 'a.en').read_text(encoding='utf-8').split()
        # the empty line never appears and only 3 valid lines exist
        # (空行は出現せず、有効行3行のみ)
        assert en_lines == ['en0', 'en1', 'en2']

    def test_rejects_a_config_without_prefixes_and_suffixes(self, tmp_path):
        '''Without prefixes/suffixes the split must not write anything

        prefixes / suffixes のどちらも無い設定では何も出力しないこと。
        '''
        src = tmp_path / 'corpus.en'
        src.write_text('a\nb\n', encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src),
            '--tags', 'a', 'b',
            '--split-sizes', '1', '1', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0
        assert not list(tmp_path.glob('a.*'))

    def test_star_split_size_takes_the_remainder(self, tmp_path):
        '''A '*' split size is filled with the lines left over

        '*' を指定した分割サイズには、残りの行が割り当てられること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        src.write_text(''.join(f'en{i}\n' for i in range(6)),
                       encoding='utf-8')
        trg.write_text(''.join(f'fr{i}\n' for i in range(6)),
                       encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src), str(trg),
            '--suffixes', 'en', 'fr',
            '--tags', 'a', 'b',
            '--split-sizes', '2', '*',
            '--random-seed', '3', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        a_lines = (tmp_path / 'a.en').read_text(encoding='utf-8').split()
        b_lines = (tmp_path / 'b.en').read_text(encoding='utf-8').split()
        # the fixed part takes exactly 2 lines, the rest go to '*'
        # (固定サイズ側は丁度2行、残りは '*' 側へ)
        assert len(a_lines) == 2
        assert len(b_lines) == 4
        assert sorted(a_lines + b_lines) == [f'en{i}' for i in range(6)]

    def test_suffixes_with_a_leading_dot_are_stripped(self, tmp_path):
        '''A leading dot of a suffix is not doubled in the output name

        suffixes の先頭ドットは出力ファイル名で二重にならないこと。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        src.write_text('en0\nen1\nen2\n', encoding='utf-8')
        trg.write_text('fr0\nfr1\nfr2\n', encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src), str(trg),
            '--suffixes', '.en', '.fr',
            '--tags', 'a', 'b',
            '--split-sizes', '1', '2',
            '--random-seed', '5', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        # the outputs keep a single extension
        # (出力には拡張子が1つだけ付く)
        assert (tmp_path / 'a.en').exists()
        assert (tmp_path / 'b.fr').exists()

    def test_empty_suffixes_name_outputs_with_the_tag_only(self, tmp_path):
        '''An empty suffix names the outputs with the tag alone

        空の suffixes ではタグ名のみで出力ファイルが作られること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        src.write_text('en0\nen1\n', encoding='utf-8')
        trg.write_text('fr0\nfr1\n', encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src), str(trg),
            '--suffixes', '', '',
            '--tags', 'a', 'b',
            '--split-sizes', '1', '1',
            '--random-seed', '5', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert (tmp_path / 'a').exists()
        assert (tmp_path / 'b').exists()

    def test_decode_failures_are_logged_as_warnings(self, monkeypatch,
                                                    tmp_path, caplog):
        '''A line that fails to convert is dropped with a warning

        変換に失敗した行は警告と共に除外されること。
        '''
        def raise_error(data):
            raise UnicodeDecodeError('utf-8', b'\xff', 0, 1,
                                     'invalid start byte')
        from lpu.common import text as text_module
        monkeypatch.setattr(text_module, 'to_unicode', raise_error)
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        src.write_text('en0\nen1\n', encoding='utf-8')
        trg.write_text('fr0\nfr1\n', encoding='utf-8')
        conf = Config()
        # to_unicode is only invoked with --ignore-empty, so enable it to
        # reach the conversion path (to_unicode は --ignore-empty 時のみ
        # 呼ばれるため、変換経路に到達するよう有効化する)
        conf.update(dict(inpaths=[str(src), str(trg)], ignore_empty=True))
        indices = random_split.get_valid_indices(conf)
        # no line survived and the failure is reported as a warning
        # (生存行は無く、失敗は警告として報告される)
        assert indices == []
        assert any('(Line 0)' in record.message for record in caplog.records)

    def test_invalid_and_negative_split_sizes_are_reported(self, tmp_path):
        '''Non-numeric sizes abort; non-positive sizes only log a warning

        数値化できない split sizes は中断し、正でない値は警告のみで
        処理継続すること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        src.write_text('en0\nen1\nen2\n', encoding='utf-8')
        trg.write_text('fr0\nfr1\nfr2\n', encoding='utf-8')
        base = ['--input', str(src), str(trg),
                '--suffixes', 'en', 'fr',
                '--tags', 'a', 'b']
        # a non-numeric size aborts the whole split
        # (数値化できないサイズでは分割全体が中断される)
        result = run_command('lpu.commands.random_split', base + [
            '--split-sizes', 'abc', '*', '--random-seed', '1', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        # nothing is written for a rejected configuration
        # (拒否された設定では何も書き出されない)
        assert not (tmp_path / 'a.en').exists()
        # a negative size is reported as non-positive and processing goes on
        # (負のサイズは正でない値として報告され、処理は継続する)
        result = run_command('lpu.commands.random_split', base + [
            '--split-sizes', '-1', '*', '--random-seed', '1',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        stderr = result.stderr.decode('utf-8', 'replace')
        assert 'split size should be positive' in stderr

    def test_count_mismatches_are_rejected_without_output(self, tmp_path):
        '''Wrong element counts for prefixes/suffixes/sizes abort cleanly

        prefixes / suffixes / split sizes の要素数不一致では
        出力無しで中断すること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        src.write_text('a\nb\n', encoding='utf-8')
        trg.write_text('x\ny\n', encoding='utf-8')
        base = ['--input', str(src), str(trg), '--tags', 'a', 'b', '--quiet']
        cases = [
            ['--prefixes', 'p1', 'p2', 'p3'],
            ['--suffixes', 's1', 's2', 's3'],
            ['--split-sizes', '1', '1', '1'],
        ]
        for extra in cases:
            # the later option of each pair wins, so the last group gets
            # the wrong element count (最後のオプションが優先され要素数が合わない)
            result = run_command('lpu.commands.random_split', base + [
                '--suffixes', 'en', 'fr', '--split-sizes', '1', '1',
            ] + extra, cwd=str(tmp_path))
            assert result.returncode == 0, (
                result.stderr.decode('utf-8', 'replace'))
            # nothing is written for a rejected configuration
            # (拒否された設定では何も書き出されない)
            assert not list(tmp_path.glob('a.*'))

    def test_missing_suffixes_default_to_empty_names(self, tmp_path):
        '''Given only prefixes, the suffix list defaults to empty strings

        prefixes のみ指定した場合、suffixes は空文字列のリストに
        フォールバックすること。
        '''
        src = tmp_path / 'corpus.en'
        src.write_text('a\nb\n', encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src),
            '--prefixes', 'out',
            '--tags', 'a', 'b',
            '--split-sizes', '1', '1', '--quiet',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        # outputs are named prefix + tag without any extension
        # (出力は拡張子無しの prefix + tag 名)
        assert (tmp_path / 'outa').exists()
        assert (tmp_path / 'outb').exists()

    def test_debug_flag_runs_to_completion(self, tmp_path):
        '''--debug only makes the logging verbose

        --debug はログを冗長にするだけで処理は完遂すること。
        '''
        src = tmp_path / 'corpus.en'
        trg = tmp_path / 'corpus.fr'
        src.write_text('a\nb\n', encoding='utf-8')
        trg.write_text('x\ny\n', encoding='utf-8')
        result = run_command('lpu.commands.random_split', [
            '--input', str(src), str(trg),
            '--suffixes', 'en', 'fr',
            '--tags', 'a', 'b',
            '--split-sizes', '1', '1', '--random-seed', '1', '--debug',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        assert (tmp_path / 'a.en').exists()


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

    def test_length_bounds_drop_long_and_short_lines(self, tmp_path):
        src = tmp_path / 'corpus.en.txt'
        trg = tmp_path / 'corpus.fr.txt'
        # line 1 is too short (1 word), line 3 too long (4 words)
        # (1行目は短すぎ (1語)、3行目は長すぎ (4語))
        src.write_text('one\none two\nw1 w2 w3 w4\n', encoding='utf-8')
        trg.write_text('e1\ne1 e2\ne1 e2 e3 e4\n', encoding='utf-8')
        result = run_command('lpu.commands.clean_parallel', [
            '--min', '2', '--max', '3', str(src), str(trg), 'cleaned',
        ], cwd=str(tmp_path))
        assert result.returncode == 0
        en_lines = (tmp_path / 'corpus.en.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        fr_lines = (tmp_path / 'corpus.fr.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        assert en_lines == ['one two']
        assert fr_lines == ['e1 e2']

    def test_normalize_escapes_special_characters(self, tmp_path):
        src = tmp_path / 'corpus.en.txt'
        trg = tmp_path / 'corpus.fr.txt'
        src.write_text('a <b>&(c)\t d\n', encoding='utf-8')
        trg.write_text('x <y>&(z)\t w\n', encoding='utf-8')
        result = run_command('lpu.commands.clean_parallel', [
            '--normalize', '--escape', '--min', '1', '--max', '20',
            str(src), str(trg), 'cleaned',
        ], cwd=str(tmp_path))
        assert result.returncode == 0
        en_lines = (tmp_path / 'corpus.en.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        fr_lines = (tmp_path / 'corpus.fr.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        # every Moses delimiter is escaped and the tab became a space
        # (Moses 系の区切り記号がエスケープされ、タブは空白化される)
        assert en_lines == ['a -LT-b-GT--AMP--LRB-c-RRB- d']
        assert fr_lines == ['x -LT-y-GT--AMP--LRB-z-RRB- w']

    def test_target_directory_option(self, tmp_path):
        src = tmp_path / 'corpus.en.txt'
        trg = tmp_path / 'corpus.fr.txt'
        src.write_text('a\n', encoding='utf-8')
        trg.write_text('x\n', encoding='utf-8')
        target = tmp_path / 'out'
        # relative source paths so that target-directory is respected
        # (target-directory が有効になるよう入力は相対パスで渡す)
        result = run_command('lpu.commands.clean_parallel', [
            '--target-directory', str(target),
            'corpus.en.txt', 'corpus.fr.txt', 'cleaned',
        ], cwd=str(tmp_path))
        assert result.returncode == 0
        # the directory is created and the cleaned files land inside
        # (ディレクトリが作成され、その中にクリーニング結果が出る)
        assert (target / 'corpus.en.txt.cleaned').read_text(
            encoding='utf-8') == 'a\n'
        assert (target / 'corpus.fr.txt.cleaned').read_text(
            encoding='utf-8') == 'x\n'

    def test_names_without_a_common_suffix_use_the_diff_naming(self, tmp_path):
        '''When basenames share no common suffix, tag + diff naming applies

        basename に共通 suffix が無い場合は tag + 差分の命名になること。
        '''
        src = tmp_path / 'doc'
        trg = tmp_path / 'doc.src'
        src.write_text('a b\n', encoding='utf-8')
        trg.write_text('x y\n', encoding='utf-8')
        result = run_command('lpu.commands.clean_parallel', [
            '--min', '1', '--max', '10', 'doc', 'doc.src', 'cleaned',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        # commonPrefix is "doc", so each output is tag + '.' + diff part
        # (commonPrefix は "doc" のため、出力は tag + '.' + 差分部分)
        assert (tmp_path / 'doc.cleaned').read_text(
            encoding='utf-8') == 'a b\n'
        assert (tmp_path / 'doc.cleaned.src').read_text(
            encoding='utf-8') == 'x y\n'

    def test_decode_failures_are_reported_and_dropped(self, monkeypatch,
                                                      tmp_path, caplog):
        '''A line failing to convert is dropped with a warning

        変換に失敗した行は警告と共に除外されること。
        '''
        def raise_error(data):
            raise UnicodeDecodeError('utf-8', b'\xff', 0, 1,
                                     'invalid start byte')
        from lpu.common import text as text_module
        monkeypatch.setattr(text_module, 'to_unicode', raise_error)
        src = tmp_path / 'corpus.en.txt'
        trg = tmp_path / 'corpus.fr.txt'
        src.write_text('valid line\nother line\n', encoding='utf-8')
        trg.write_text('x1\nx2\n', encoding='utf-8')
        caplog.clear()
        cleanParallel(srcFilePaths=[str(src), str(trg)], outTag='cleaned',
                      min=1, max=10, target_directory=str(tmp_path))
        # the failing row is reported with its line number and dropped
        # (失敗した行は行番号付きで報告され、出力から除外される)
        assert any('(Line 0)' in record.message for record in caplog.records)
        en_lines = (tmp_path / 'corpus.en.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        fr_lines = (tmp_path / 'corpus.fr.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        assert en_lines == []
        assert fr_lines == []

    def test_invalid_byte_sequences_are_escaped_not_dropped(self, tmp_path):
        '''Undecodable bytes become backslash escapes, not a failure

        デコードできないバイト列は例外ではなくバックスラッシュ
        エスケープ文字列として出力されること。
        '''
        src = tmp_path / 'corpus.en.txt'
        trg = tmp_path / 'corpus.fr.txt'
        src.write_bytes(b'\xff broken\nvalid line\n')
        trg.write_text('x1\nx2\n', encoding='utf-8')
        result = run_command('lpu.commands.clean_parallel', [
            '--min', '1', '--max', '10', str(src), str(trg), 'cleaned',
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        en_lines = (tmp_path / 'corpus.en.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        fr_lines = (tmp_path / 'corpus.fr.txt.cleaned').read_text(
            encoding='utf-8').splitlines()
        # the byte 0xff became the literal text "\xff" and the line is kept
        # (0xff はリテラルの "\xff" 文字列になり、行は保持される)
        assert en_lines == ['\\xff broken', 'valid line']
        assert fr_lines == ['x1', 'x2']

    def test_get_diff_with_a_non_empty_suffix(self):
        '''getDiff removes both the common prefix and suffix

        getDiff は共通 prefix と suffix の両方を取り除くこと。
        '''
        from lpu.commands.clean_parallel import getDiff
        assert getDiff('doc.cleaned.src', 'doc.cleaned', '.src') == ''
        assert getDiff('doc.cleaned.body', 'doc', '') == '.cleaned.body'


class TestDialog:
    def test_continue_with_an_empty_yes_default(self):
        result = run_command('lpu.commands.dialog',
                             ['--continue', '--yes'], input_bytes=b'\n')
        assert result.returncode == 0

    def test_continue_with_a_no_answer_exits_nonzero(self):
        result = run_command('lpu.commands.dialog',
                             ['--continue', '--no'], input_bytes=b'\n')
        assert result.returncode == 1

    def test_continue_loops_until_a_valid_answer(self, tmp_path):
        result = run_command('lpu.commands.dialog',
                             ['--continue', '--yes'],
                             input_bytes=b'maybe\nno\n')
        # an invalid first answer is asked again, then "no" aborts
        # (最初の無効な回答は再度問われ、"no" で中断される)
        assert result.returncode == 1
        stderr = result.stderr.decode('utf-8', 'replace')
        assert stderr.count('Do you want to continue?') == 2

    def test_exist_asks_only_when_the_file_exists(self, tmp_path):
        missing = tmp_path / 'missing.txt'
        result = run_command('lpu.commands.dialog', ['--exist', str(missing),
                                                    '--no'],
                             input_bytes=b'n\n')
        # no prompt happened, so stdin was left unread
        # (問い合わせは行われず、そのまま終了する)
        assert result.returncode == 0
        target = tmp_path / 'target.txt'
        target.write_text('x', encoding='utf-8')
        result = run_command('lpu.commands.dialog', ['--exist', str(target),
                                                    '--no'],
                             input_bytes=b'n\n')
        assert result.returncode == 1

    def test_without_flags_exits_nonzero(self):
        result = run_command('lpu.commands.dialog', [])
        assert result.returncode == 1


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

    def test_debug_flag_runs_without_quiet(self, tmp_path):
        target = tmp_path / 'exists.txt'
        target.write_text('x', encoding='utf-8')
        result = run_command('lpu.commands.wait_files',
                             ['--debug', '--interval', '1', str(target)])
        assert result.returncode == 0


@requires_smt
class TestWordAlign:
    '''End-to-end training and scoring of the IBM models

    IBM モデルの学習とスコアリングの end-to-end テスト。
    '''

    EXPECTED_ALIGNMENT = {
        'the': 'le', 'cat': 'chat', 'dog': 'chien',
        'sat': 'assis', 'ran': 'couru', 'a': 'un',
    }

    def _train_and_read_best(self, tmp_path, corpus, tag):
        '''Train on the corpus and return the best translation of each word

        コーパスで学習し、各語の最も確率の高い訳語を返す。
        '''
        src_path, trg_path = corpus
        trans_path = tmp_path / (f'trans_{tag}.txt')
        align_path = tmp_path / (f'align_{tag}.txt')
        result = run_command('lpu.smt.align.ibm_models', [
            '--iteration-limit', '10', '--quiet',
            str(src_path), str(trg_path), str(trans_path), str(align_path),
        ], cwd=str(tmp_path), entry='main_train')
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')

        best = {}
        for line in trans_path.read_text(encoding='utf-8').splitlines():
            fields = line.split('\t')
            if len(fields) < 3:
                continue
            source, target, probability = fields[0], fields[1], float(fields[2])
            if source not in best or probability > best[source][1]:
                best[source] = (target, probability)
        return best

    def test_train_learns_the_expected_alignment(self, tmp_path,
                                                 parallel_corpus):
        best = self._train_and_read_best(tmp_path, parallel_corpus, 'lf')
        for source, target in self.EXPECTED_ALIGNMENT.items():
            assert source in best, f'missing source word: {source}'
            assert best[source][0] == target, (
                f'expected {source} -> {target}, got {best[source][0]}')

    def test_train_handles_a_crlf_corpus(self, tmp_path, crlf_parallel_corpus):
        '''A CRLF corpus must give the same alignment as an LF one

        progress.FileReader reads bytes and decodes them itself, so it
        applies no newline translation. 0.2.x stripped only LF, which left a
        stray CR in the last word of every source line and produced a
        corrupted vocabulary.

        CRLF のコーパスでも LF と同じアライメントが得られること。
        progress.FileReader はバイトで読んで自前でデコードするため改行変換を
        行わない。0.2.x は LF のみを除去していたため、原言語側の各行末の語に
        CR が残り、語彙が壊れていた。
        '''
        best = self._train_and_read_best(tmp_path, crlf_parallel_corpus, 'crlf')
        assert '' not in best, 'an empty source word was registered'
        for source, target in self.EXPECTED_ALIGNMENT.items():
            assert source in best, f'missing source word: {source}'
            assert best[source][0] == target, (
                f'expected {source} -> {target}, got {best[source][0]}')

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
