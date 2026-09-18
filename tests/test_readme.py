# -*- coding: utf-8 -*-

'''Validate the shell command examples in the README files

Every ```shell block of README.md / README.ja.md is checked:

- the leading command of each `$` line is either a registered entry point
  of the package (parsed from [project.scripts] of pyproject.toml) or a
  known external command available on PATH,
- for lpu commands, every long option written in the usage example really
  exists in the command's `--help` output.

This catches README updates that are forgotten when an entry point is
renamed or an option is dropped from a command.

README ファイル内の shell コードブロックに書かれたコマンド例を検証する。
- 各 `$` 行の先頭コマンドが、pyproject.toml の [project.scripts] に登録
  済みのエントリポイント、または PATH 上で解決できる既知の外部コマンド
  と一致すること
- lpu 系コマンドの usage 例に書かれた各ロングオプションが、実際の
  --help 出力に存在すること

エントリポイントの改名やオプション削除時に README への反映が漏れた
場合にこのテストが失敗する。
'''

import re
import shutil
from pathlib import Path

import pytest

from conftest import _module_available
from test_commands import run_command


REPO_ROOT = Path(__file__).resolve().parent.parent

README_FILES = ['README.md', 'README.ja.md']

# External commands referenced by the README install / development examples.
# Missing ones are skipped (e.g. uv is not installed in every test
# environment), while unknown commands always fail.
# (README のインストール・開発手順に出てくる外部コマンド。
#  無い場合はスキップ (例: uv が無い環境)、未知のコマンドは常に失敗)
EXTERNAL_COMMANDS = {'pip', 'uv'}

# `$ cmd` / continuation lines of ```shell blocks
FENCE_PATTERN = re.compile(r'^```shell\s*$\n(.*?)^```[ \t]*$', re.M | re.S)


def _shell_commands(path: Path) -> "list[tuple[int, str]]":
    '''Extract the (line number, joined command) pairs of a README file

    Backslash-continued lines are joined so that multi-line usage examples
    are treated as a single command.

    README ファイルから (行番号, 連結済みコマンド) の一覧を取り出す。
    行末のバックスラッシュによる継続行は連結し、複数行の usage 例を
    1 つのコマンドとして扱う。
    '''
    # README.ja.md is UTF-8; the platform default would break on Windows
    # (README.ja.md は UTF-8。プラットフォーム既定では Windows で壊れる)
    text = path.read_text(encoding='utf-8')
    results = []
    for match in FENCE_PATTERN.finditer(text):
        start_line = text.count('\n', 0, match.start(1)) + 1
        block = match.group(1)
        lines = block.splitlines()
        # join backslash continuations first
        # (まずバックスラッシュによる継続行を連結する)
        joined = []
        buf = ''
        start_buf = 0
        for offset, line in enumerate(lines):
            stripped = line.strip()
            if buf:
                buf += ' ' + stripped
            else:
                buf = stripped
                start_buf = offset
            if buf.endswith('\\'):
                buf = buf[:-1].strip()
            else:
                joined.append((start_buf, buf))
                buf = ''
        if buf:
            # a trailing continuation with no following line
            # (末尾が継続行のまま終わった場合)
            joined.append((start_buf, buf))
        for offset, command in joined:
            if not command.startswith('$'):
                continue
            line_no = start_line + offset + 1
            results.append((line_no, command[1:].strip()))
    return results


def _load_scripts() -> "dict[str, tuple[str, str]]":
    '''Parse [project.scripts] of pyproject.toml into {name: (module, entry)}

    pyproject.toml の [project.scripts] を {コマンド名: (モジュール, 関数)}
    の辞書として取り出す。
    '''
    pattern = re.compile(r'^"?(lpu-[\w-]+)"?\s*=\s*"([^:"]+):(\w+)"')
    scripts = {}
    for line in (REPO_ROOT / 'pyproject.toml').read_text(
            encoding='utf-8').splitlines():
        match = pattern.match(line.strip())
        if match:
            scripts[match.group(1)] = (match.group(2), match.group(3))
    return scripts


def _all_commands() -> "list[tuple[str, int, str]]":
    '''Collect the (file, line, command) triples of every README file

    全 README ファイルから (ファイル名, 行番号, コマンド) を集める。
    '''
    triples = []
    for name in README_FILES:
        for line_no, command in _shell_commands(REPO_ROOT / name):
            triples.append((name, line_no, command))
    return triples


def _lpu_commands() -> "list[tuple[str, str]]":
    '''Collect the unique (command name, full command) pairs of lpu commands

    shell 例の中から lpu 系コマンドの (コマンド名, コマンド全体) を重複
    なく集める。
    '''
    pairs = []
    seen = set()
    for _, _, command in _all_commands():
        first = _first_token(command)
        if first.startswith('lpu-') and first not in seen:
            seen.add(first)
            pairs.append((first, command))
    return pairs


def _first_token(command: str) -> str:
    '''Return the leading command name, skipping environment assignments

    環境変数設定 (VAR=value) のトークンを読み飛ばし、最初のコマンド名を
    返す。
    '''
    for token in command.split():
        if '=' in token:
            continue
        return token
    return ''


def _long_options(command: str) -> "list[str]":
    '''Extract the long option names written in a usage example

    usage 例に書かれたロングオプション名 (--xxx) を抽出する。
    '''
    return re.findall(r'(?<![\w-])(--[a-z][a-z0-9-]*)', command)


SCRIPTS = _load_scripts()


@pytest.mark.parametrize('name,line_no,command', _all_commands(),
                         ids=['%s:%s' % (n, l) for n, l, _ in _all_commands()])
def test_command_is_known(name, line_no, command):
    '''The leading command of a README example must be resolvable

    README のコマンド例の先頭は、パッケージのエントリポイントか
    解決可能な外部コマンドでなければならない。
    '''
    first = _first_token(command)
    assert first, 'empty command at %s:%s' % (name, line_no)
    scripts = SCRIPTS
    if first.startswith('lpu-'):
        assert first in scripts, (
            '"%s" at %s:%s is not registered in [project.scripts] '
            'of pyproject.toml' % (first, name, line_no)
        )
    elif first in EXTERNAL_COMMANDS:
        # skipped, not failed, when the external tool is absent, so that
        # minimal environments (e.g. cibuildwheel test runs) still pass
        # (外部ツールが無い場合は失敗ではなくスキップ。cibuildwheel の
        #  テスト実行のような最小環境でも動くようにするため)
        if shutil.which(first) is None:
            pytest.skip('%s is not installed' % first)
    else:
        raise AssertionError(
            'unknown command "%s" at %s:%s' % (first, name, line_no)
        )


@pytest.mark.parametrize('command_name,command', _lpu_commands())
def test_usage_options_exist(command_name, command):
    '''Every long option of a lpu usage example must exist in its --help

    lpu 系コマンドの usage 例に書かれたロングオプションは、実際の
    --help 出力に存在しなければならない。
    '''
    module, entry = SCRIPTS[command_name]
    if command_name.startswith('lpu-smt-'):
        # the smt commands need the compiled extensions, numpy and pycedar,
        # which are not installable in every wheel test environment
        # (smt 系コマンドはコンパイル済み拡張と numpy / pycedar を必要とし、
        #  環境によっては導入できないためスキップする)
        if not _module_available('lpu.smt.trans_models.tables'):
            pytest.skip('lpu.smt.trans_models is not available')
    # the abbreviated lpu-smt-* examples ("[-h] ...") have no options
    # to check beyond the help run itself
    # (省略形の lpu-smt-* 例 ("[-h] ...") では --help の実行自体が検査)
    process = run_command(module, ['--help'], entry=entry)
    assert process.returncode == 0, (
        '%s --help failed: %s' % (command_name, process.stderr)
    )
    help_text = process.stdout.decode()
    options = _long_options(command)
    missing = [opt for opt in options if opt not in help_text]
    assert not missing, (
        'options %s of "%s" are not in its --help output'
        % (missing, command_name)
    )