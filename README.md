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

#### lpu.smt.align.ibm_models

utility classes to train and estimate word alignemt based on IBM models

## Commands

LPU package also includes directly executable commands 

### commands in `lpu` package

#### lpu-abspath

```shell
  $ lpu-abspath [-h] filepath [filepath ...]
```

get absolute paths of given files or directories

#### lpu-clean-parallel

```shell
  $ lpu-clean-parallel [-h] [--min min_length] [--max max_length] \
      [--ratio ratio] [--target-directory directory_path] [--escape] \
      [--normalize] filepath [filepath ...] output_tag
```

#### lpu-dialog

```shell
  $ lpu-dialog [-h] [--exist filepath] [--continue] [--yes] [--no]
```

Show message on condition, wait and receive user's response

#### lpu-exec-parallel

```shell
  $ lpu-exec-parallel [-h] [--input filepath] [--output filepath] \
      [--splitsize num_lines] [--chunks num_files] [--threads num_threads] \
      [--tmpdir directory_path] [--verbose] [--interval seconds] command
```

Execute command in multiple processes by splitting the targe file

#### lpu-guess-langcode

```shell
  $ lpu-guess-langcode [-h] filepath [filepath ...]
```

Guess the language codes from given files

#### lpu-progress

```shell
  $ lpu-progress [-h] [--lines] [--refresh seconds] [--header string] \
      [filepath filepath ...]]
```

Show the progress of pipe I/O

#### lpu-random-split

```shell
  $ lpu-random-split [-h] --input filepath [filepath ...] \
      [--prefixes prefix [prefix ...]] [--suffixes suffix [suffix ...]] \
      --tags tag [tag ...] --split-sizes size [size ...] [--ignore-empty] \
      [--quiet] [--debug] [--random-seed seed] [--ids [suffix]]
```

#### lpu-wait-files

```shell
  $ lpu-wait-files [-h] [--quiet] [--debug] [--delay seconds] \
      [--interval seconds] [--timeout seconds] filepath [filepath ...]
```

Wait until file will be found

#### lpu-word-align-train

```shell
  $ lpu-word-align-train [-h] [--save-sores filepath] [--decode-align filepath] \
      [--iteration-limit num_iterations] [--threshold min_probability] \
      [--nbest integer] [--character] [--debug] [--quiet] \
      src_path trg_path save_trans_path [save_align_path]
```

#### lpu-word-align-score

```shell
  $ lpu-word-align-score [-h] [--save-scores filepath] \
      [--decode-align filepath] [--character] [--debug] [--quiet] \
      src_path trg_path trans_path [align_path]
```
