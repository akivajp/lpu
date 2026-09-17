# -*- coding: utf-8 -*-

'''Run the doctests embedded in the annotated modules

型注釈を整えたモジュールに埋め込んだ doctest を実行する。
doctest を含むモジュールは純 Python のものだけを選んでいるため、
コンパイル済み拡張の無い環境でも収集・実行できる。

例の追加方法: 対象モジュールの公開関数の docstring に
``>>>`` 形式の例を書き、以下の DOCTEST_MODULES にモジュールを
登録する (docstring 例は日本語コメントを含む説明と併記する)。
'''

import doctest
from importlib import import_module

import pytest

# Modules whose docstring examples are executed as tests
# (docstring 例を実際に実行して検証するモジュール)
DOCTEST_MODULES = [
    'lpu.common.colors',
    'lpu.common.numbers',
    'lpu.common.text',
    'lpu.common.validation',
    'lpu.data_structs.trees',
    'lpu.metrics.bleu',
    'lpu.metrics.ribes',
]

# ELLIPSIS allows "..." placeholders, IGNORE_EXCEPTION_DETAIL keeps the
# UnicodeDecodeError example independent of the exact message wording.
# (ELLIPSIS で "..." 省略記法、IGNORE_EXCEPTION_DETAIL で例外メッセージの
#  細部の違いを許容する)
OPTIONFLAGS = doctest.ELLIPSIS | doctest.IGNORE_EXCEPTION_DETAIL


def _collect_doctests():
    '''Enumerate every DocTest in DOCTEST_MODULES

    DOCTEST_MODULES に属する全 DocTest オブジェクトを集める。
    '''
    cases = []
    for module_name in DOCTEST_MODULES:
        module = import_module(module_name)
        finder = doctest.DocTestFinder(exclude_empty=True)
        cases.extend(finder.find(module, module_name))
    return cases


def pytest_generate_tests(metafunc):
    if 'doctest_case' in metafunc.fixturenames:
        cases = _collect_doctests()
        ids = ['%s#%s' % (case.name, i)
               for i, case in enumerate(cases)]
        metafunc.parametrize('doctest_case', cases, ids=ids)


def test_doctest(doctest_case):
    '''Run one DocTest and fail when any of its examples mismatch

    1 件の DocTest を実行し、例がひとつでも期待どおりでなければ失敗する。
    '''
    runner = doctest.DocTestRunner(optionflags=OPTIONFLAGS)
    runner.run(doctest_case)
    summary = runner.summarize(verbose=False)
    assert summary.failed == 0, summary