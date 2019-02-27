#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

from setuptools import findall
from setuptools import find_packages
from setuptools import setup
from setuptools import Extension

import numpy

MAIN_PACKAGE = 'lpu'

if sys.platform == 'linux2':
    from distutils import sysconfig
    # Omitting 'strict-prototypes' warning For Python 2.x
    opt = sysconfig.get_config_vars().get('OPT', '')
    opt = opt.replace('-Wstrict-prototypes', '')
    sysconfig.get_config_vars()['OPT'] = opt
    # Omitting 'strict-prototypes' warning For Python 3.x
    cflags = sysconfig.get_config_vars().get('CFLAGS', '')
    cflags = cflags.replace('-Wstrict-prototypes', '')
    sysconfig.get_config_vars()['CFLAGS'] = cflags

def get_package(path):
    if os.path.exists( os.path.join(path, '__init__.py') ):
        dirpath = os.path.dirname( os.path.abspath(str(path)) )
        parent = get_package(dirpath)
        if parent:
            return parent + '.' + os.path.basename(path)
        return os.path.basename(path)
    return ''

def get_modules(dirpath, suffixes=['.pyx'], additional_sources=None, **options):
    modules = []
    for path in findall(dirpath):
        if isinstance(suffixes, str):
            suffixes = [suffixes]
        if not any([path.endswith(suffix) for suffix in suffixes]):
            continue
        dirpath = os.path.dirname(path)
        module = os.path.splitext( os.path.basename(path) )[0]
        package = get_package(dirpath)
        if package:
            module = package + '.' + module
        sources = [path]
        if additional_sources:
            sources = sources + list(additional_sources)
        modules.append( Extension(module, sources, **options) )
    return modules

include_dirs = [
    numpy.get_include(),
]

try:
    from Cython.Build import build_ext
    from Cython.Build import cythonize
    compiler_directives = dict(
        language_level = sys.version_info[0],
    )
    ext_modules = get_modules(
        MAIN_PACKAGE, ['.pyx'],
        include_dirs = include_dirs,
    )
    ext_modules = cythonize(
        ext_modules,
        compiler_directives = compiler_directives,
    )
    cmdclass = {'build_ext': build_ext}
except ImportError:
    ext_modules = get_modules(
        MAIN_PACKAGE, ['.c', '.cpp'],
        include_dirs = include_dirs,
    )
    cmdclass = {}

version_file = os.path.join(os.path.dirname(__file__), MAIN_PACKAGE, 'VERSION')
version = open(version_file).read().strip()

install_requires = [
    #'Cython',
    'numpy',
]

setup(
    name = 'lpu',
    version = version,
    cmdclass = cmdclass,
    ext_modules = ext_modules,
    install_requires = install_requires,
    description = 'A Language Processing Utility',
    long_description = open('README.md').read(),
    long_description_content_type = 'text/markdown',
    url = 'https://github.com/akivajp/lpu',
    author = 'Akiva Miura',
    author_email = 'akiva.miura@gmail.com',
    license = 'MIT',
    keywords = [
        'CL',
        'NLP',
        'computational linguistics',
        'natural language processing',
    ],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Utilities",
    ],
    packages = find_packages(),
    package_data = {
        '': [
            '*.pxd',
            '*.pyx',
        ],
        'lpu': [
            'VERSION'
        ],
    },
    entry_points = {
        'console_scripts': [
            'lpu-abspath = lpu.commands.abspath:main',
            'lpu-clean-parallel= lpu.commands.clean_parallel:main',
            'lpu-dialog  = lpu.commands.prompt:main',
            'lpu-exec-parallel= lpu.commands.exec_parallel:main',
            'lpu-guess-langcode= lpu.commands.guess_langcode:main',
            'lpu-progress= lpu.commands.progress:main',
            'lpu-random-split= lpu.commands.random_split:main',
            'lpu-train-ibm-model1= lpu.smt.align.ibm_model1:main_train',
            #'lpu-score-ibm-model1= lpu.smt.align.ibm_model1:main_score',
            'lpu-wait-files= lpu.commands.wait_files:main',
        ],
    },
)

