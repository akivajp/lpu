# LPU

![version](https://img.shields.io/pypi/v/lpu.svg)
![python](https://img.shields.io/pypi/pyversions/lpu.svg)
![license](https://img.shields.io/pypi/l/lpu.svg)

`LPU` is a collection of utility classes/functions for language processing.

日本語版のドキュメントは [README.ja.md](README.ja.md) にあります。

## Requirements

- Python 3.10 or later

The core features depend only on the standard library. The features listed
under [Optional features](#optional-features) additionally require the
`smt` extra.

## Installation

### Installing from PyPI release

```shell
$ pip install lpu
```

To also use the word alignment models and the Double-Array Trie:

```shell
$ pip install 'lpu[smt]'
```

### Installing from GitHub master

```shell
$ pip install 'lpu[smt] @ git+https://github.com/akivajp/lpu.git'
```

## Modules

### lpu.common.config

Inheritable and serializable configuration classes, useful for calling
functions with many arguments.

```python
from lpu.common.config import Config

conf = Config({'threshold': 0.5, 'nested': {'depth': 3}})
conf.update(threshold=0.8)
print(conf.data.threshold)   # 0.8
print(conf['nested.depth'])  # 3
print(conf.to_json())        # {"threshold": 0.8, "nested": {"depth": 3}}
```

A `Config` keeps two layers: values passed positionally form the inherited
*base* layer, while values assigned afterwards go to the *main* layer.
`to_dict()` returns the main layer only; pass `upstream=True` (the default
of `to_json()`) to include the inherited values.

### lpu.common.environ

Handling environment variables with stacks, useful for changing and
reverting global settings such as debugging modes.

```python
import os
from lpu.common import environ

with environ.push(LPU_DEBUG='1') as layer:
    layer.set('MY_SETTING', 'temporary')
    ...
# both variables are restored here
```

Only variables assigned through `set()` (or given to `push()`) are tracked
and restored.

### lpu.common.files

Utility functions for file handling, including transparent access to gzip
files.

```python
from lpu.common import files

# opens plain or gzip files alike, detected by extension and magic number
with files.open('corpus.txt.gz', 'rt') as f:
    for line in f:
        ...

files.getContentSize('corpus.txt.gz')  # uncompressed size
files.wait_file('lockfile', timeout=60)
```

### lpu.common.logging

Enhanced logging objects (built on the standard `logging` library) with
colorizing features and control through environment variables.

```python
from lpu.common import logging

logger = logging.getColorLogger(__name__)
with logging.using_config(__name__, debug=True):
    some_variable = 42
    logger.debug_print(some_variable)   # some_variable => int(42)
```

`debug_print` parses the caller's source line, so the printed value is
labelled with the expression it came from. The level follows the
`LPU_DEBUG` / `DEBUG` and `LPU_QUIET` / `QUIET` environment variables.

### lpu.common.progress

Utility classes and functions for progress reporting (progress bars) that
work with file-type objects and iterators.

```python
from lpu.common import files, progress

# progress over a gzip file is measured by the position in the
# compressed stream, so the percentage is known without decompressing
# the whole file first
for line in progress.view(files.open('corpus.txt.gz', 'rb'), 'loading'):
    ...

for item in progress.view(iter(range(1000)), 'processing'):
    ...
```

### lpu.common.text

Conversion between `bytes` and `str`: `to_str` (tolerates invalid byte
sequences), `to_unicode` (strict) and `to_bytes`.

### lpu.common.numbers

`toNumber` converts a value to `int` when it is close enough to an integer,
plus `intToBytes` / `intFromBytes`.

### lpu.common.colors

`put_color` wraps text in ANSI escape sequences.

### lpu.common.validation

`check_argument_type` raises a `TypeError` with a readable message listing
the expected types.

### lpu.common.vocab

`StringEnumerator` maps strings to sequential IDs and back. The
phrase-level helpers (`phrase2id`, `id2phrase`, `phraseMap`) are backed by
the Double-Array Trie and therefore need the `smt` extra; the enumerator
itself does not.

### lpu.data_structs.trees

Tree expressions and operations: `TreeNode`, `parseSExpression`,
`calcEditDistance` (sequence edit distance) and `calcTreeEditDistance`.

```python
from lpu.data_structs import trees

tree = trees.TreeNode.fromS('(S (NP the cat) (VP sat))')
trees.calcEditDistance('kitten', 'sitting')                       # 3
trees.calcTreeEditDistance('(S (NP a))', '(S (NP b))')            # 1
```

### lpu.metrics

Evaluation metrics for machine translation.

```python
from lpu.metrics import bleu, ribes

ref = 'the cat sat on the mat'.split()
hyp = 'the cat sat on a mat'.split()
bleu.eval_bleu(ref, hyp, 4)
ribes.eval_ribes(ref, hyp)
```

`bleu` is a simple sentence-level implementation with no tokenization of
its own; use [sacrebleu](https://github.com/mjpost/sacrebleu) for
publishable, comparable scores. `ribes` implements
`NKT * P**alpha * BP**beta` following Isozaki et al. (2010).

## Optional features

These require the `smt` extra (`pip install 'lpu[smt]'`), which pulls in
`numpy` and `pycedar`, and a compiled build of the package.

### lpu.data_structs.trie

Dictionaries and ID maps implemented on a Double-Array Trie: `IDMap`,
`TwoWayIDMap` and `Dict`.

### lpu.smt.align.ibm_models

Classes to train and estimate word alignment based on the IBM models
(model 1 and model 2).

### lpu.smt.trans_models

Records, tables and operations over Moses / Travatar style phrase and rule
tables, including phrase table triangulation for pivot translation.

These modules come from work on statistical machine translation and are
kept for reference; for current word alignment work, tools such as
`fast_align`, `awesome-align` or `SimAlign` are the usual choice.

## Commands

LPU also installs directly executable commands.

### lpu-abspath

```shell
$ lpu-abspath [-h] filepath [filepath ...]
```

Get absolute paths of given files or directories.

### lpu-clean-parallel

```shell
$ lpu-clean-parallel [-h] [--min min_length] [--max max_length] \
    [--ratio ratio] [--target-directory directory_path] [--escape] \
    [--normalize] filepath [filepath ...] output_tag
```

Filter a parallel corpus by length and length ratio, keeping the lines of
every side aligned.

### lpu-dialog

```shell
$ lpu-dialog [-h] [--exist filepath] [--continue] [--yes] [--no]
```

Show a message on condition, wait and receive the user's response.

### lpu-exec-parallel

```shell
$ lpu-exec-parallel [-h] [--input filepath] [--output filepath] \
    [--splitsize num_lines] [--chunks num_files] [--threads num_threads] \
    [--tmpdir directory_path] [--verbose] [--interval seconds] command
```

Execute a command in multiple processes by splitting the target file.

### lpu-guess-langcode

```shell
$ lpu-guess-langcode [-h] filepath [filepath ...]
```

Guess the language codes from the given file names.

### lpu-progress

```shell
$ lpu-progress [-h] [--lines] [--refresh seconds] [--header string] \
    [filepath [filepath ...]]
```

Show the progress of pipe I/O.

### lpu-random-split

```shell
$ lpu-random-split [-h] --input filepath [filepath ...] \
    [--prefixes prefix [prefix ...]] [--suffixes suffix [suffix ...]] \
    --tags tag [tag ...] --split-sizes size [size ...] [--ignore-empty] \
    [--quiet] [--debug] [--random-seed seed] [--ids [suffix]]
```

Split a parallel corpus at random into several parts, keeping the line
correspondence between the sides. One of `--prefixes` or `--suffixes` is
required.

### lpu-wait-files

```shell
$ lpu-wait-files [-h] [--quiet] [--debug] [--delay seconds] \
    [--interval seconds] [--timeout seconds] filepath [filepath ...]
```

Wait until the files are found.

### Word alignment commands

```shell
$ lpu-word-align-train [-h] [--save-scores filepath] \
    [--decode-align filepath] [--iteration-limit num_iterations] \
    [--threshold min_probability] [--nbest integer] [--character] \
    [--debug] [--quiet] src_path trg_path save_trans_path [save_align_path]

$ lpu-word-align-score [-h] [--save-scores filepath] \
    [--decode-align filepath] [--character] [--debug] [--quiet] \
    src_path trg_path trans_path [align_path]
```

Train the IBM word alignment models on a parallel corpus, and score or
decode alignments with a trained model. Requires the `smt` extra.

### Phrase / rule table commands

```shell
$ lpu-smt-convert-extract [-h] ...
$ lpu-smt-filter [-h] ...
$ lpu-smt-make-glue-rules [-h] ...
$ lpu-smt-normalize [-h] ...
$ lpu-smt-triangulate [-h] ...
```

Operations over Moses / Travatar style phrase and rule tables.
`lpu-smt-triangulate` builds a pivot phrase table from two tables sharing
a pivot language. Requires the `smt` extra. Pass `--help` to each command
for its options.

## Development

```shell
$ uv sync
$ uv run pytest
```

The test suite runs against an editable build, so the C extensions are
exercised. Tests that need the extensions, `numpy` or `pycedar` skip
themselves when those are unavailable.

To install without building any C extension:

```shell
$ LPU_NO_EXTENSIONS=1 pip install .
```

## License

MIT. See [LICENSE](LICENSE).
