# LPU

![version](https://img.shields.io/pypi/v/lpu.svg)
![python](https://img.shields.io/pypi/pyversions/lpu.svg)
![license](https://img.shields.io/pypi/l/lpu.svg)

`LPU` is a collection of utility classes/functions for language processing

## Installation

### Installing from PyPI release

```shell
$ pip install --user lpu
```

### Installing from GitHub master

```shell
$ pip install --user https://github.com/akivajp/lpu/archive/master.zip
```

## Modules

### modules in `lpu` package

#### lpu.common.config

  inheritable and serializable configurutation classes, useful for calling functions with many arguments

#### lpu.common.environ

  handling environment variables with stacks, useful for changing/reverting global settings, such as debugging modes

#### lpu.common.files

  utility functions for file handling, including transparent file access of gzip files

#### lpu.common.logging

  enhanced logging objects (from standard logging library) with colorizing features and operations with environment variables

#### lpu.common.progress

  utility classes and functions for progress reporting (as known as progress bars), working with file-type objects and iterators

