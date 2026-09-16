#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Build definition for the C/C++ extension modules

All package metadata (name, version, dependencies, CLI entry points) lives
in pyproject.toml; this file is only responsible for declaring which
extension modules to build.

Only the modules that directly use C++ containers or numpy typed arrays
need to be compiled by Cython. Everything else (most of lpu.common.*,
lpu.commands.*, lpu.metrics.* and so on) works as pure Python and is
deliberately excluded from compilation, which makes the build far less
likely to break as Python versions advance.

C/C++ 拡張モジュールのビルド定義。

パッケージのメタデータ (名前・バージョン・依存関係・CLI 登録) は
すべて pyproject.toml 側に記述しており、このファイルはビルド対象の
拡張モジュールを宣言することだけを担当する。

Cython によるコンパイルが必要なのは、C++ コンテナや numpy の型付き
配列を直接使っているモジュールのみである。それ以外のモジュール
(lpu.common.* の大半、lpu.commands.*、lpu.metrics.* など) は
純 Python として動作するため、意図的にコンパイル対象から除外している。
これにより、Python のバージョンが上がってもビルドが破綻しにくくなる。
'''

import os
import sys

from setuptools import Extension
from setuptools import setup

# ---------------------------------------------------------------------------
# Build configuration / ビルド設定
# ---------------------------------------------------------------------------

# Setting LPU_NO_EXTENSIONS=1 skips building the extensions entirely,
# for using only the pure Python part or for debugging purposes.
# 環境変数 LPU_NO_EXTENSIONS=1 で拡張モジュールのビルドを完全に省略できる
# (純 Python 部分のみを使いたい場合や、デバッグ目的での利用を想定)
NO_EXTENSIONS = os.environ.get('LPU_NO_EXTENSIONS', '') not in ('', '0', 'false', 'False')

# Modules that must be compiled by Cython.
# The parenthesised note gives the reason compilation is mandatory.
# Cython でコンパイルする必要のあるモジュール。括弧内はコンパイルが必須である理由。
CYTHON_SOURCES = [
    # Holds a C++ std::deque<std::string> directly (see trie.pxd)
    # C++ の std::deque<std::string> を直接保持している (trie.pxd 参照)
    'lpu/data_structs/trie.py',
    # EM loops of the IBM models over numpy typed arrays
    # numpy の型付き配列による IBM モデルの EM ループ
    'lpu/smt/align/ibm_model1.pyx',
    'lpu/smt/align/ibm_model2.pyx',
    'lpu/smt/align/ibm_models.pyx',
    # cdef classes processing phrase tables of millions of lines
    # フレーズテーブル (数百万行) を処理する cdef class 群
    'lpu/smt/trans_models/records.pyx',
    'lpu/smt/trans_models/tables.pyx',
]


def _source_to_module(path):
    '''Convert a source file path into a Python module name

    ソースファイルのパスを Python のモジュール名に変換する。
    '''
    stem = os.path.splitext(path)[0]
    return stem.replace(os.sep, '.').replace('/', '.')


def _get_extra_compile_args():
    '''Return options that suppress compiler warnings (on supported platforms)

    コンパイラ警告を抑制するオプションを返す (対応環境のみ)。
    '''
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        # Suppress numpy deprecated-API warnings and sign-comparison
        # warnings from Cython-generated code.
        # numpy の非推奨 API 警告と、Cython 生成コードの符号比較警告を抑制
        return ['-Wno-cpp', '-Wno-sign-compare', '-Wno-unreachable-code']
    return []


def _build_ext_modules():
    '''Build the list of Cython extension modules

    Returns an empty list when Cython or numpy is unavailable, so that the
    pure Python part alone can still be installed.

    Cython 拡張モジュールの一覧を構築する。
    Cython または numpy が利用できない場合は空リストを返し、
    純 Python 部分のみをインストールできるようにする。
    '''
    if NO_EXTENSIONS:
        return []
    try:
        from Cython.Build import cythonize
        import numpy
    except ImportError as exc:
        sys.stderr.write(
            'warning: skipping C extensions ({}). '
            'lpu.smt.* and lpu.data_structs.trie will be unavailable.\n'.format(exc)
        )
        return []

    extra_compile_args = _get_extra_compile_args()
    extensions = [
        Extension(
            _source_to_module(path),
            sources=[path],
            language='c++',
            include_dirs=[numpy.get_include()],
            extra_compile_args=extra_compile_args,
            # optional=True keeps the installation itself successful even if
            # compilation fails, as a safety net so that at least the pure
            # Python part remains usable.
            # optional=True: コンパイルに失敗してもインストール自体は成功させる。
            # 純 Python 部分だけでも利用できる状態を保つための保険。
            optional=True,
        )
        for path in CYTHON_SOURCES
    ]
    return cythonize(
        extensions,
        compiler_directives={
            'language_level': '3',
            'embedsignature': True,
        },
    )


setup(ext_modules=_build_ext_modules())
