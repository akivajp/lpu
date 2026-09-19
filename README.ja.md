# LPU

![test](https://github.com/akivajp/lpu/actions/workflows/test.yml/badge.svg)
![version](https://img.shields.io/pypi/v/lpu.svg)
![python](https://img.shields.io/pypi/pyversions/lpu.svg)
![license](https://img.shields.io/pypi/l/lpu.svg)

`LPU` (Language Processing Utilities) は、言語処理向けのユーティリティ
クラス・関数を集めたパッケージです。

English documentation is available in [README.md](README.md).

## 動作要件

- Python 3.10 以降

コア機能は標準ライブラリのみに依存します。
[オプション機能](#オプション機能) に挙げた機能のみ `smt` / `trie`
エクストラを追加で必要とします。

## インストール

### PyPI から

```shell
$ pip install lpu
```

単語アライメントモデルも利用する場合:

```shell
$ pip install 'lpu[smt]'
```

Double-Array Trie も利用する場合:

```shell
$ pip install 'lpu[smt,trie]'
```

### GitHub の master から

```shell
$ pip install 'lpu[smt,trie] @ git+https://github.com/akivajp/lpu.git'
```

## モジュール

### lpu.common.config

継承可能・シリアライズ可能な設定クラス。引数の多い関数を呼び出す際に
便利です。

```python
from lpu.common.config import Config

conf = Config({'threshold': 0.5, 'nested': {'depth': 3}})
conf.update(threshold=0.8)
print(conf.data.threshold)   # 0.8
print(conf['nested.depth'])  # 3
print(conf.to_json())        # {"threshold": 0.8, "nested": {"depth": 3}}
```

`Config` は 2 層構造を持ちます。位置引数で渡した値は継承層 (base) に入り、
その後に代入した値は上書き層 (main) に入ります。`to_dict()` は上書き層
のみを返すため、継承層も含めるには `upstream=True` を指定します
(`to_json()` は既定で含めます)。

### lpu.common.environ

環境変数をスタックとして扱うモジュール。デバッグモードのような
グローバル設定を一時的に変更して元に戻す用途に使えます。

```python
import os
from lpu.common import environ

with environ.push(LPU_DEBUG='1') as layer:
    layer.set('MY_SETTING', 'temporary')
    ...
# ここで両方の変数が復元される
```

復元の対象になるのは `set()` 経由 (または `push()` の引数) で設定した
変数のみです。

### lpu.common.files

ファイル入出力の補助関数。gzip ファイルへの透過的なアクセスを含みます。

```python
from lpu.common import files

# 拡張子とマジックナンバーで判定し、非圧縮/gzip を同じように開く
with files.open('corpus.txt.gz', 'rt') as f:
    for line in f:
        ...

files.getContentSize('corpus.txt.gz')  # 展開後のサイズ
files.wait_file('lockfile', timeout=60)

# safe_* 系は、対象が存在しないことをエラーとせず戻り値で伝え、
# それ以外の OSError は握り潰さずに送出します
files.safe_remove('workdir/*.tmp')        # 削除した件数を返す
files.safe_copy('model.bin', 'model.bak')
files.safe_link('model.bin', 'latest')    # ハードリンク、不可ならシンボリックリンク
files.safe_rename('model.tmp', 'model.bin')  # 改名先が存在しても置き換える
```

### lpu.common.logging

標準 `logging` を拡張したロガー。色付き出力と、環境変数による制御に
対応します。

```python
from lpu.common import logging

logger = logging.getColorLogger(__name__)
with logging.using_config(__name__, debug=True):
    some_variable = 42
    logger.debug_print(some_variable)   # some_variable => int(42)
```

`debug_print` は呼び出し元のソース行を解析するため、出力された値が
どの式から来たものかがラベル付けされます。ログレベルは環境変数
`LPU_DEBUG` / `DEBUG` および `LPU_QUIET` / `QUIET` に従います。

### lpu.common.progress

ファイルオブジェクトやイテレータに対する進捗表示 (プログレスバー)。

```python
from lpu.common import files, progress

# gzip ファイルの進捗は圧縮ストリーム上の位置で測るため、
# 事前に全体を展開しなくても進捗率が分かる
for line in progress.view(files.open('corpus.txt.gz', 'rb'), 'loading'):
    ...

for item in progress.view(iter(range(1000)), 'processing'):
    ...
```

### lpu.common.text

`bytes` と `str` の相互変換。`to_str` (不正なバイト列を許容)、
`to_unicode` (厳密)、`to_bytes` を提供します。

### lpu.common.numbers

`toNumber` は整数に十分近い値を `int` に変換します。
`intToBytes` / `intFromBytes` も含みます。

### lpu.common.colors

`put_color` はテキストを ANSI エスケープシーケンスで囲みます。

### lpu.common.validation

`check_argument_type` は、期待される型を列挙した読みやすいメッセージ
付きで `TypeError` を送出します。

### lpu.common.vocab

`StringEnumerator` は文字列と連番 ID を相互変換します。
フレーズ単位の補助関数 (`phrase2id`, `id2phrase`, `phraseMap`) は
Double-Array Trie を用いるため `trie` エクストラが必要ですが、
`StringEnumerator` 自体には不要です。

`IDMap` は同じ考え方をより高機能にした語彙クラスです。特殊記号
`<pad>` / `<s>` / `</s>` / `<unk>` を予約し、各トークンの出現頻度を数え、
高頻度語のみへの切り詰めや、テキストファイルへの保存・読み込みが行えます。

```python
from lpu.common.vocab import IDMap, LabelMap

idmap = IDMap()
idmap.feed_corpus('train.tsv', 0)   # 0 列目を 1 行ずつ投入する
idmap.truncate(32000)               # 特殊記号 + 高頻度語のみ残す
idmap.save('vocab.txt')

ids = idmap.encode('the cat', add_symbols=True)  # bos / eos で囲む
idmap.decode(ids)                               # 'the cat'
```

`LabelMap` はラベルフィールド向けの `IDMap` で、1 つのフィールドに重み付きの
複数ラベル (`positive:3 negative:1`) を書けます。`str2dist()` はこれを
正規化した確率分布に、`str2score()` は数値ラベルの期待値に変換します。

```python
labels = LabelMap()
labels.feed_field('positive negative')
labels.str2dist('positive:3 negative:1')  # [0.75, 0.25]
```

### lpu.data_structs.trees

木構造の表現と操作。`TreeNode`、`parseSExpression`、
`calcEditDistance` (系列の編集距離)、`calcTreeEditDistance` を提供します。

```python
from lpu.data_structs import trees

tree = trees.TreeNode.fromS('(S (NP the cat) (VP sat))')
trees.calcEditDistance('kitten', 'sitting')                       # 3
trees.calcTreeEditDistance('(S (NP a))', '(S (NP b))')            # 1
```

### lpu.metrics

機械翻訳の評価指標。

```python
from lpu.metrics import bleu, ribes

ref = 'the cat sat on the mat'.split()
hyp = 'the cat sat on a mat'.split()
bleu.eval_bleu(ref, hyp, 4)
ribes.eval_ribes(ref, hyp)
```

`bleu` は文単位の簡易実装で、独自のトークナイズは行いません。
論文等に載せる比較可能なスコアには
[sacrebleu](https://github.com/mjpost/sacrebleu) を使ってください。
`ribes` は Isozaki et al. (2010) に従い
`NKT * P**alpha * BP**beta` を計算します。

## オプション機能

以下は `smt` エクストラ (`pip install 'lpu[smt]'`) と、コンパイル済み
ビルドを必要とします。エクストラにより `numpy` が入ります。
Double-Array Trie はさらに `pycedar` を必要とし、`trie` エクストラ
(`pip install 'lpu[smt,trie]'`) で導入されます (Windows 向けの
`pycedar` wheel は提供されていないため、Windows では利用できません)。

### lpu.data_structs.trie

Double-Array Trie による辞書と ID マップ。`IDMap`、`TwoWayIDMap`、
`Dict` を提供します。

### lpu.smt.align.ibm_models

IBM モデル (Model 1 / Model 2) に基づく単語アライメントの学習と推定。

### lpu.smt.trans_models

Moses / Travatar 形式のフレーズテーブル・ルールテーブルに対する
レコード、テーブル、各種操作。ピボット翻訳のためのフレーズテーブル
三角測量 (triangulation) を含みます。

これらは統計的機械翻訳 (SMT) 時代の研究成果であり、参照用として
維持しています。現在の単語アライメント用途では `fast_align` /
`awesome-align` / `SimAlign` などが一般的な選択肢です。

## コマンド

LPU は直接実行可能なコマンドも一緒にインストールします。

### lpu-abspath

```shell
$ lpu-abspath [-h] filepath [filepath ...]
```

指定したファイル・ディレクトリの絶対パスを取得します。

### lpu-clean-parallel

```shell
$ lpu-clean-parallel [-h] [--min min_length] [--max max_length] \
    [--ratio ratio] [--target-directory directory_path] [--escape] \
    [--normalize] filepath [filepath ...] output_tag
```

対訳コーパスを長さと長さ比でフィルタします。各言語側の行の対応は
保たれます。

### lpu-dialog

```shell
$ lpu-dialog [-h] [--exist filepath] [--continue] [--yes] [--no]
```

条件に応じてメッセージを表示し、ユーザーの応答を待って受け取ります。

### lpu-exec-parallel

```shell
$ lpu-exec-parallel [-h] [--input filepath] [--output filepath] \
    [--splitsize num_lines] [--chunks num_files] [--threads num_threads] \
    [--tmpdir directory_path] [--verbose] [--interval seconds] command
```

対象ファイルを分割して、コマンドを複数プロセスで実行します。

### lpu-guess-langcode

```shell
$ lpu-guess-langcode [-h] filepath [filepath ...]
```

ファイル名から言語コードを推測します。

### lpu-progress

```shell
$ lpu-progress [-h] [--lines] [--refresh seconds] [--header string] \
    [filepath [filepath ...]]
```

パイプ入出力の進捗を表示します。

### lpu-random-split

```shell
$ lpu-random-split [-h] --input filepath [filepath ...] \
    [--prefixes prefix [prefix ...]] [--suffixes suffix [suffix ...]] \
    --tags tag [tag ...] --split-sizes size [size ...] [--ignore-empty] \
    [--quiet] [--debug] [--random-seed seed] [--ids [suffix]]
```

対訳コーパスをランダムに複数へ分割します。言語側の間の行対応は
保たれます。`--prefixes` か `--suffixes` のいずれかが必要です。

### lpu-wait-files

```shell
$ lpu-wait-files [-h] [--quiet] [--debug] [--delay seconds] \
    [--interval seconds] [--timeout seconds] filepath [filepath ...]
```

指定したファイルが見つかるまで待機します。

### 単語アライメント系コマンド

```shell
$ lpu-word-align-train [-h] [--save-scores filepath] \
    [--decode-align filepath] [--iteration-limit num_iterations] \
    [--threshold min_probability] [--nbest integer] [--character] \
    [--debug] [--quiet] src_path trg_path save_trans_path [save_align_path]

$ lpu-word-align-score [-h] [--save-scores filepath] \
    [--decode-align filepath] [--character] [--debug] [--quiet] \
    src_path trg_path trans_path [align_path]
```

対訳コーパスで IBM 単語アライメントモデルを学習し、学習済みモデルで
アライメントのスコア計算やデコードを行います。`smt` エクストラが必要です。

### フレーズ/ルールテーブル系コマンド

```shell
$ lpu-smt-convert-extract [-h] ...
$ lpu-smt-filter [-h] ...
$ lpu-smt-make-glue-rules [-h] ...
$ lpu-smt-normalize [-h] ...
$ lpu-smt-triangulate [-h] ...
```

Moses / Travatar 形式のフレーズテーブル・ルールテーブルに対する操作です。
`lpu-smt-triangulate` はピボット言語を共有する 2 つのテーブルから
ピボットフレーズテーブルを構築します。`smt` エクストラが必要です。
各コマンドのオプションは `--help` を参照してください。

## 開発

```shell
$ uv sync
$ uv run pytest
```

テストは editable ビルドに対して実行されるため、C 拡張も実際に動作
検証されます。拡張・`numpy`・`pycedar` を必要とするテストは、それらが
利用できない場合は自動的にスキップされます。

C 拡張を一切ビルドせずにインストールする場合:

```shell
$ LPU_NO_EXTENSIONS=1 pip install .
```

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。
