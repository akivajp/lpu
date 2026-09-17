# Changelog

日本語版は [CHANGELOG.ja.md](CHANGELOG.ja.md) にあります。

## 0.5.0 (2026-09-18)

### Added

- Windows wheels, built by the release workflow. `pycedar` publishes no
  Windows wheel, so the `lpu[smt]` extra no longer pulls it in.
- Coverage measurement of the test suite: the command tests measure
  their subprocesses too, and a CI job runs the suite with coverage and
  uploads the combined data. Suite coverage is measured at 67%.
- Docstring examples (doctests) in `lpu.common.numbers`, `text`,
  `colors`, `validation`, `lpu.data_structs.trees`, `lpu.metrics.bleu`
  and `ribes`, executed by `tests/test_doctests.py`.
- End-to-end tests for `lpu-smt-filter`, `lpu-smt-normalize`,
  `lpu-smt-make-glue-rules` and `lpu-smt-convert-extract`, which
  previously had none.

### Breaking changes

- The `lpu[smt]` extra now installs `numpy` only. `pycedar`, which backs
  the Double-Array Trie (`lpu.data_structs.trie`), moved to the new
  `lpu[trie]` extra. Install `lpu[smt,trie]` for the previous set.
  On Windows, `lpu[smt]` now installs successfully.

## 0.4.0 (2026-09-18)

### Added

- `lpu/py.typed`, marking the package as typed (PEP 561), so downstream
  type checkers now recognize the annotations.
- Type annotations for `lpu.common.numbers`, `lpu.common.validation`,
  `lpu.common.colors`, `lpu.common.vocab`, `lpu.metrics.bleu`,
  `lpu.metrics.ribes` and `lpu.data_structs.trees`.
- `ruff` and `mypy` checks: the CI runs a lint job, and the annotated
  modules are type-checked (gradually; see `[tool.mypy]` in
  `pyproject.toml`).
- End-to-end tests for `lpu-smt-triangulate`, which previously had only
  a `--help` smoke test: rule triangulation, the `prodprob` probability
  multiplication, alignment merging through the pivot and the gzip
  output.

### Fixed

- The error-path logging calls raised `AttributeError` instead of
  logging: `lpu.common.logging` never had module-level `warn`, `debug`
  or `log` functions, but the exception handlers of
  `lpu-clean-parallel`, `lpu-smt-normalize`, `lpu-smt-triangulate` and
  the compiled `records` / `tables` modules called them. They now use
  per-module loggers.
- `Table.find` / `Table.find_src` always raised
  `TypeError: find_keys() got an unexpected keyword argument 'force'`,
  because the nonexistent `force` kwarg was forwarded to every released
  version of `pycedar` (0.2.0 - 0.4.0). The `force` parameter is kept in
  the method signatures for compatibility but is no longer forwarded.
- Bare `except:` clauses were made explicit (`except Exception`, and
  `except OSError` in `safeMakeDirs`).
- Raw `open()` calls now pass `encoding='utf-8'` in text mode, instead
  of depending on the locale, and file handles are closed properly
  (`lpu/__init__.py`, `lpu-clean-parallel`, `lpu-exec-parallel`,
  `lpu-smt-triangulate`, `lpu-smt-make-glue-rules`).
- `lpu-random-split` now shows a description in its `--help` output,
  like every other command.

## 0.3.0 (2026-09-17)

This release makes the package installable and usable again on current
Python versions. Version 0.2.10 (2020-03) shipped wheels for CPython
3.5-3.7 only, and building from the sdist always failed because `setup.py`
imported `numpy` without declaring it as a build dependency, so `pip
install lpu` could not succeed on Python 3.8 or later. Of the ten CLI
commands, six failed on import even when a build was forced.

### Breaking changes

- **Python 3.10 or later is required.** Python 2 support and the
  compatibility layer are gone.
- `lpu.common.compat` is deprecated. It remains as a thin alias that warns
  on import; use `lpu.common.text` and the standard library instead. The
  Python-2-only helpers (`py2_*`, `convert_struct`) were removed.
- The `lpu.backends` package (`safe_cython`, `safe_logging`) was removed.
- `lpu.data_structs.trie.TwoWayIDMap.items()` now yields `(key, ID)`,
  matching `IDMap.items()` in the parent class; it used to yield
  `(ID, key)`.
- `lpu.data_structs.trie` raises `ImportError` when `pycedar` is missing.
  It used to call `sys.exit(1)`, terminating the host process.
- The `.pxd` files of the pure Python modules were removed, so those
  modules can no longer be `cimport`ed from Cython code.
- `lpu.common.numbers` no longer exposes the Python 2 variants of
  `intToBytes` / `intFromBytes`.

### Packaging

- Added `pyproject.toml`, declaring the build requirements
  (setuptools / Cython / numpy), the project metadata and the entry points.
  `pip install lpu` now works under build isolation.
- `setup.py` is reduced to the extension build definition and no longer
  uses `distutils`, which was removed in Python 3.12.
- Only the modules that genuinely need Cython are compiled:
  `data_structs/trie` (C++ `std::deque<std::string>`), `smt/align/*`
  (numpy typed EM loops) and `smt/trans_models/{records,tables}` (cdef
  classes on the hot path). The rest of the package is pure Python.
- The extensions are marked `optional`, and `LPU_NO_EXTENSIONS=1` skips
  them entirely, so installation succeeds without a toolchain.
- The SMT dependencies are declared as the `smt` extra (`numpy`,
  `pycedar>=0.2.0`).
- Added the missing `LICENSE` file (MIT was already declared in
  `setup.py`).

### Added

- `lpu.common.text` with `to_str`, `to_unicode` and `to_bytes`.
- `lpu.metrics.ribes.eval_ribes`, which actually computes RIBES
  (`NKT * P**alpha * BP**beta`, Isozaki et al. 2010). The module
  previously provided only the word order correlation, so RIBES itself
  could not be computed. Also added `calc_brevity_penalty`,
  `calc_normalized_kendalls_tau` and `calc_word_orders`.
- `lpu.data_structs.trees.TreeNode.fromS` now parses an S-expression; it
  used to ignore its argument and return an empty node.
- Five commands for the phrase and rule table tools, which had a `main()`
  but were never registered and so were unreachable:
  `lpu-smt-convert-extract`, `lpu-smt-filter`, `lpu-smt-make-glue-rules`,
  `lpu-smt-normalize` and `lpu-smt-triangulate`.
- A pytest suite under `tests/`, replacing the four assertion-free scripts
  under `test/`, and GitHub Actions workflows for tests and releases.
- `README.ja.md` and this changelog.

### Fixed

Bugs that were independent of the Python version and had been present in
0.2.x:

- `common.config`: `Config.update(**kwargs)` always raised, because
  `_update_data` rejected `_conf=None`. This made `lpu-word-align-train`
  unusable on every Python version. The error message of the same function
  was missing its `.format()` call, and updating from a `ConfigData`
  instance failed because `__main` was looked up as a class attribute.
- `common.files`: `getContentSize()` called `gzip.read32()`, which no
  longer exists, so it always returned `-1` and silently disabled progress
  reporting over gzip files. `rawsize()` returned a size one byte too
  small. `is_gzipped()` decompressed a line instead of checking the magic
  number.
- `common.environ`: `get_env()` returned the `default` only when
  `system=False`, so a missing key returned `None` with the default
  arguments. `StackHolder.unset()` discarded the records of every other
  variable in the layer. Layers were pushed onto the shared `env_stack`
  and never removed.
- `common.logging`: `using_config()` passed `debug` where `quiet` was
  meant, and `get_quiet_status()` read `QUIET` while `set_quiet()` writes
  `LPU_QUIET`, so quiet mode could never be enabled. `LoggingConfig`
  defined `unset_debug` twice, the second shadowing the first; the second
  is now `unset_quiet`.
- `common.progress`: `pipe_view()` never called `outfunc`, using it only as
  a flag to suppress the stdout write, so the content was discarded.
- `data_structs.trees`: `TreeNode.checkValid(deep=True)` reported any node
  with children as invalid, because the recursive condition was commented
  out while its `return False` was left behind. A stray debug `print()` in
  the recursive body of `calcTreeEditDistance` was removed.
- `data_structs.trie`: `TwoWayIDMap.ids/items/keys` typed the C++
  `std::string` elements as Python objects, so all three raised
  `AttributeError`. The module was migrated to the dict-compatible API of
  `pycedar` 0.2 (`num_keys()`, `predict()` and `erase()` were removed
  there); verified against `pycedar` 0.3.1 as well.
- `metrics.ribes`: in the word alignment, a context window match was
  compared against 2 occurrences instead of 1, and a word absent from the
  reference fell through a no-op `pass` instead of being skipped.
- Python 3 incompatibilities: `from collections import Iterable` (removed
  in 3.10), the bare `long` type names left over from Python 2, string
  comparison by identity and invalid escape sequences.

### Removed

- 418 lines of commented-out code (about 10% of the tree): Cython
  declaration comments duplicating the `.pxd` declarations, commented
  `@cython` decorators, commented-out debug output and imports, and
  comments duplicating an existing line of real code.

## 0.2.10 (2020-03-02)

See the git history for earlier releases.
