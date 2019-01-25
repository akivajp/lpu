#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from setuptools import findall
from setuptools import find_packages
from setuptools import setup
from Cython.Distutils import build_ext
from Cython.Build import cythonize

extensions = [
    'lpu/common/*.pyx',
    'lpu/data_structs/*.pyx',
    'lpu/smt/align/*.pyx',
]

compiler_directives = dict(
    language_level = sys.version_info[0],
)

ext_modules = cythonize(
    extensions,
    compiler_directives = compiler_directives,
    exclude='*.py',
)

setup(
    name = 'lpu',
    version = '0.0.2',
    cmdclass = {'build_ext': build_ext},
    #cmdclass = cmdclass,
    ext_modules = ext_modules,
    #packages = find_packages(),
    packages = find_packages(),
    package_data = {'': '*.pyx'},
    description = 'A Language Process Utility',
    url = 'https://github.com/akivajp/lpu',
    author = 'Akiva Miura',
    author_email = 'akiva.miura@gmail.com',
    license = 'MIT',
    entry_points = {
        'console_scripts': [
            'lpu-abspath = lpu.commands.abspath:main',
            'lpu-clean-parallel= lpu.commands.clean_parallel:main',
            'lpu-dialog  = lpu.commands.prompt:main',
            'lpu-exec-parallel= lpu.commands.exec_parallel:main',
            'lpu-guess-langcode= lpu.commands.guess_langcode:main',
            'lpu-progress= lpu.commands.progress:main',
            'lpu-random-split= lpu.commands.random_split:main',
            'lpu-train-ibm-model1= lpu.smt.align.ibm_model1:main',
            'lpu-wait-files= lpu.commands.wait_files:main',
        ],
    },
)

def clean():
    print("CLEAN")
