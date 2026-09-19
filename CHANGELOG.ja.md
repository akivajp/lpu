# 変更履歴

English version is available in [CHANGELOG.md](CHANGELOG.md).

## 未リリース

### 追加

- `lpu.common.vocab` に `IDMap` と `LabelMap` を追加しました。作者の未公開の
  PyTorch 研究コードから移植したものです。`IDMap` は特殊記号
  `<pad>` / `<s>` / `</s>` / `<unk>` を予約し、トークンの出現頻度を数え、
  高頻度語への切り詰めやテキストファイルへの保存・読み込みが行える語彙
  クラスです。`LabelMap` はこれをラベルフィールド向けに特化したもので、
  重み付きの複数ラベル (`positive:3 negative:1`) を確率分布、または
  数値ラベルの期待値に変換します。いずれも標準ライブラリのみに依存し、
  既存の `StringEnumerator` / `word2id` 系には手を加えていません。
  移植に際して、元実装の以下の不具合を修正しました:
  `encode()` が組み立てた ID を返さず暗黙の `None` を返していた、
  `decode()` が `remove_symbols` 引数を無視していた、区切り文字が `None` の
  ときに `feed_field()` がフィールド全体と空白分割したトークンの両方を
  登録していた、`str2dist()` が語彙を拡張する前に長さを決めた分布ベクトルを
  参照していた (未知ラベル初出で `IndexError`) 上に、重み付きラベルの後に
  続く重み無しラベルを取りこぼしていた、語彙ファイルの読み書きが
  プラットフォーム既定のエンコーディングだった (Windows で非 ASCII
  トークンが壊れる)。
- `lpu.common.files` に、同じコードから `safe_remove` / `safe_copy` /
  `safe_link` / `safe_rename` を追加しました。共通の規約として、対象が
  存在しないことは例外ではなく戻り値で伝え、それ以外の `OSError` は
  送出します (権限エラーが静かなデータ欠損に化けないようにするため)。
  `safe_rename` は `os.replace` を用いるため Windows でも改名先を置き換え
  られます。`safe_link` はハードリンクを作れない場合にシンボリックリンクへ
  フォールバックします。
- `lpu.metrics.ranking` を追加しました。`calc_precision_at_k` と
  `calc_mean_reciprocal_rank` でランカーを評価します。順位が `None`
  (未検出) の場合は例外ではなく不正解として数え、空の順位列や 0 以下の
  順位は 0 除算ではなく明示的に弾きます。

### 修正

- coverage ジョブだけ `actions/upload-artifact@v4` を使っており、他の
  ステップは `v7` でした。`v7` に統一しました。
- `indexTree` が空リストノードに対して暗黙の `None` を返しており、
  呼び出し側で `TypeError` によりクラッシュしていました。他の異常系の
  入力と同様、未訪問の左範囲 `-1` を返すようになりました。

### 変更

- `mypy` が未注釈関数の本体も検査するようになり
  (`check_untyped_defs`, `disallow_untyped_defs`)、型付き関数からの
  `Any` 返却 (`warn_return_any`) や厳格な等値性・指令の検査
  (`strict_equality`, `warn_unused_ignores`) も有効になりました。
  残っていた未注釈関数には注釈を追加し、`Any` を返していた経路は
  宣言型への `cast` で明示しました。
- CI ランナーを `ubuntu-24.04` に明示ピン留めしました。`ubuntu-latest`
  の Ubuntu 26 への自動移行 (2026-10-19) を先回りして回避するもので、
  実際の移行は後日意図的に実施します。
- ruff の flake8-comprehensions (`C4`) と ruff 固有ルール (`RUF`) を
  有効化し、指摘された 22 件を修正しました: 冗長な `list()` / `dict()`
  呼び出し、`math.ceil()` / `round()` (既に int を返す) の余分な
  `int()` ラップ、`all()` へのリスト内包引数、リスト連結の展開化への
  書き換え、未使用のアンパック変数、参照のみのクラス属性への
  `ClassVar` 注釈。挙動の変更はありません。

## 0.5.2 (2026-09-18)

### 修正

- `lpu-random-split` で、分割サイズが数値でない場合に
  `UnboundLocalError` (それを潜り抜けた場合は後段の `float()`) で
  クラッシュしていました。他の設定検証失敗と同様に設定を中断する
  ようになりました。
- `lpu-exec-parallel` で、空の入力に対して `numChunks` が未設定のまま
  `AttributeError` でクラッシュしていました。チャンク数 0 として記録し、
  空の出力で正常終了するようになりました。また `--chunks 0` は検証を
  通過した後 `ZeroDivisionError` でクラッシュしていましたが、他の不正値と
  同様に拒否されるようになりました。

### 追加

- `lpu.common.logging`、残りの大規模 `lpu.commands` モジュール
  (`exec_parallel`, `clean_parallel`, `random_split`) および純 Python の
  `lpu.smt.trans_models` モジュール (`convert_extract`, `filter`,
  `make_glue_rules`, `normalize`, `triangulate`) に型注釈を追加し、
  `mypy` の検査対象が 27 モジュールになりました。
- パッケージの quiet / debug 初期化 (利用できない C 拡張の報告を含む)、
  `lpu.common.environ` と `colors` の失敗分岐、`lpu-exec-parallel` の
  協調動作の経路 (モジュールカバレッジ 84% → 99%)、トライアンギュレーションの
  multi-target とツリー照合の経路、`lpu-smt-normalize` の multi-target
  経路、および `lpu-random-split` / `lpu-clean-parallel` の追加分岐に
  テストを追加しました。テスト数は 476 から 497 に、スイートの
  カバレッジは 85% から 91% に向上しました。

### 変更

- ruff の pyupgrade ルール (`UP`) でコードベースを現代化しました。
  printf 形式と `.format()` の文字列フォーマットを f-string へ、
  `super()` 呼び出しから冗長な引数を除去し、`# -*- coding: utf-8 -*-`
  宣言や自明な `object` 継承を削除しました。抽象型は
  `collections.abc` からインポートします。これに伴い、
  `lpu.common.logging` の Python 2 用デッドコードも削除されました。
- テストワークフローは、コンパイル済み EM 拡張が無い環境で word-align の
  使用例テストを SMT コマンドと同様にスキップするようになり、lint ジョブは
  `setup.py` も対象にするようになりました。

## 0.5.1 (2026-09-18)

### 修正

- `lpu-smt-triangulate` とフレーズ/ルールテーブル系ツールが、2.x 時代の
  移行漏れにより Python 3 上で動作しない状態でした。`map` オブジェクトの
  添字アクセス、`dict.values()[0]`、名前ではなく添字での features アクセス、
  リネーム前の `co` 属性と `co=` キーワード引数、Python から見えない
  `cdef` の `round()` メソッド、`Table.find_src()` が常に渡す `hiero`
  キーワードに応答しない `Record.getSymbols()` を修正しました。
  レコードの読み込みとルールのトライアンギュレーションが再び動作します。
- ロガーを指定せずに生成した `LoggingConfig` が `_reconfigureLogger()`
  内で `AttributeError` で落ちていました。空のロガーセットを既定値に
  するようになりました。
- `assert False` によるガードを明示的な `AssertionError` 送出に置き換え、
  `python -O` 下でも例外が発生するようにしました。`lpu-smt-normalize`
  がレコード処理の失敗時に送出する例外には文言と元例外 (cause) が
  含まれるようになりました。
- `.mode` 属性が int になるファイルオブジェクト (Python 3.12 以前の
  `gzip.GzipFile` など) に対して `files.is_mode()` が `AttributeError`
  で落ちていました。これにより CI の wheel テスト実行が失敗していました。
- 更新間隔の経過時間が 0.0 になった場合に `progress.SpeedCounter.view()`
  が `ZeroDivisionError` を送出したり、`reset()` が活動後の改行を
  出力しなかったりすることがありました (いずれも Windows の粗い
  `time.time()` 分解能が原因です)。活動の判定を時計ではなく出力フラグに
  よるものに変更しました。

### 追加

- レコード読み込みとトライアンギュレーションのテスト (34件)、
  `lpu.common.logging` の内部処理のテスト、`lpu-random-split` の
  `--ids` / `--ignore-empty` オプション、`lpu-clean-parallel` の
  長さ制限 / 正規化 / `--target-directory` の各経路、dialog ヘルパー、
  `lpu.common.config` の例外分岐 (カバレッジ 100%) のテストを追加
  しました。スイート全体のカバレッジは 67% から 85% に向上しました。
- `lpu.common.config`, `files`, `environ`, `dialog`, `progress` および
  小規模な `lpu.commands` モジュールに型注釈を追加し、`mypy` の検査対象が
  18 モジュールになりました。
- `ruff` の bugbear (`B`) ルールを有効化し、指摘された18件の欠陥を
  修正しました。

### 変更

- 対訳コーパスのループは行数不一致の入力を短い側で打ち切る従来動作を
  維持しつつ、許容が意図された箇所の `zip()` では `strict=False` を、
  長さが保証される箇所では `strict=True` を明示するようにしました。

## 0.5.0 (2026-09-18)

### 追加

- Windows 向け wheel をリリースワークフローでビルドするようにしました。
  `pycedar` は Windows 用 wheel を公開していないため、`lpu[smt]` エクストラ
  は pycedar を含まなくなりました。
- テストスイートのカバレッジ計測を導入しました。コマンドテストは
  サブプロセス側も計測し、CI ジョブがカバレッジ付きでテストを実行して
  統合データを成果物として残します。スイート全体のカバレッジは 67% です。
- `lpu.common.numbers`, `text`, `colors`, `validation`,
  `lpu.data_structs.trees`, `lpu.metrics.bleu`, `ribes` の docstring に
  実行例 (doctest) を追加し、`tests/test_doctests.py` が実行します。
- `lpu-smt-filter`, `lpu-smt-normalize`, `lpu-smt-make-glue-rules`,
  `lpu-smt-convert-extract` の end-to-end テストを追加しました (従来は
  テストがありませんでした)。

### 破壊的変更

- `lpu[smt]` エクストラは `numpy` のみを導入するようになりました。
  Double-Array Trie (`lpu.data_structs.trie`) を支える `pycedar` は
  新設の `lpu[trie]` エクストラに移りました。従来と同じ依存セットは
  `lpu[smt,trie]` で導入できます。なお Windows では `lpu[smt]` が
  正常にインストールできるようになりました。

## 0.4.0 (2026-09-18)

### 追加

- `lpu/py.typed` を追加しました (PEP 561)。これによりパッケージが型注釈を
  公開していることが下流の型チェッカーに認識されます。
- `lpu.common.numbers`, `lpu.common.validation`, `lpu.common.colors`,
  `lpu.common.vocab`, `lpu.metrics.bleu`, `lpu.metrics.ribes`,
  `lpu.data_structs.trees` に型注釈を追加しました。
- `ruff` と `mypy` による検査を導入しました。CI に lint ジョブを追加し、
  型注釈済みモジュールは型検査されます (`pyproject.toml` の
  `[tool.mypy]` 参照、段階的に拡大予定)。
- `lpu-smt-triangulate` の end-to-end テストを追加しました。従来は
  `--help` の疎通のみでした。ルールの三角化、`prodprob` による確率の
  乗算、pivot を経由するアライメントの連結、gzip 出力を検証します。

### 修正

- 例外発生時のログ出力が `AttributeError` を送出していました。
  `lpu.common.logging` にはモジュールレベルの `warn` / `debug` / `log`
  関数が存在しないにも関わらず、`lpu-clean-parallel`,
  `lpu-smt-normalize`, `lpu-smt-triangulate` およびコンパイル済みの
  `records` / `tables` の例外ハンドラから呼び出されていました。
  モジュールごとの logger を用いる形式に置き換えました。
- `Table.find` / `Table.find_src` が常に
  `TypeError: find_keys() got an unexpected keyword argument 'force'`
  となっていました。存在しない `force` 引数を pycedar に転送していたためで、
  リリース済みの全バージョン (0.2.0〜0.4.0) で発生します。
  `force` 引数は API 互換のためシグネチャに残していますが、
  pycedar へは転送しなくなりました。
- bare `except:` を明示化しました (`except Exception` へ、
  `safeMakeDirs` は `except OSError`)。
- テキストモードで生の `open()` を呼び出している箇所に `encoding='utf-8'`
  を明示し、ロケール依存を解消しました。併せてファイルハンドルを確実に
  クローズするようにしました (`lpu/__init__.py`, `lpu-clean-parallel`,
  `lpu-exec-parallel`, `lpu-smt-triangulate`, `lpu-smt-make-glue-rules`)。
- `lpu-random-split` の `--help` に他のコマンド同様 `description` を
  表示するようにしました。

## 0.3.0 (2026-09-17)

現行の Python でパッケージを再びインストール・利用できるようにする
リリースです。0.2.10 (2020-03) は CPython 3.5〜3.7 向けの wheel のみを
公開しており、`setup.py` が `numpy` をビルド依存として宣言せずに import
していたため sdist からのビルドも必ず失敗していました。その結果
Python 3.8 以降では `pip install lpu` が成功し得ない状態でした。
また、無理にビルドを通しても 10 個の CLI コマンドのうち 6 個が
import 時に失敗していました。

### 破壊的変更

- **Python 3.10 以降が必須**になりました。Python 2 サポートと互換レイヤは
  廃止しました。
- `lpu.common.compat` を非推奨にしました。import 時に警告を出す薄い
  エイリアスとして残していますが、`lpu.common.text` と標準ライブラリへ
  移行してください。Python 2 専用の補助関数 (`py2_*`, `convert_struct`)
  は削除しました。
- `lpu.backends` パッケージ (`safe_cython`, `safe_logging`) を削除しました。
- `lpu.data_structs.trie.TwoWayIDMap.items()` が親クラス
  `IDMap.items()` と同じ `(キー, ID)` を返すようになりました
  (従来は `(ID, キー)`)。
- `lpu.data_structs.trie` は `pycedar` が無い場合に `ImportError` を
  送出します。従来は `sys.exit(1)` を呼び出してホストプロセスを
  終了させていました。
- 純 Python 化したモジュールの `.pxd` を削除したため、それらを Cython
  コードから `cimport` することはできなくなりました。
- `lpu.common.numbers` から Python 2 版の
  `intToBytes` / `intFromBytes` を削除しました。

### パッケージング

- `pyproject.toml` を追加し、ビルド要件 (setuptools / Cython / numpy)、
  プロジェクトメタデータ、エントリポイントを宣言しました。
  ビルド分離下でも `pip install lpu` が動作します。
- `setup.py` は拡張モジュールのビルド定義のみに縮小し、Python 3.12 で
  削除された `distutils` への依存を撤去しました。
- Cython コンパイルの対象を、真に必要なモジュールのみに限定しました:
  `data_structs/trie` (C++ の `std::deque<std::string>`)、
  `smt/align/*` (numpy 型付きの EM ループ)、
  `smt/trans_models/{records,tables}` (ホットパスの cdef クラス)。
  それ以外は純 Python です。
- 拡張モジュールを `optional` として宣言し、`LPU_NO_EXTENSIONS=1` で
  完全に省略できるようにしたため、コンパイル環境が無くても
  インストールが成功します。
- SMT 系の依存関係を `smt` エクストラ (`numpy`, `pycedar>=0.2.0`) として
  宣言しました。
- 欠けていた `LICENSE` ファイルを追加しました
  (MIT は `setup.py` で宣言済みでした)。

### 追加

- `lpu.common.text` (`to_str`, `to_unicode`, `to_bytes`)。
- `lpu.metrics.ribes.eval_ribes`。実際に RIBES
  (`NKT * P**alpha * BP**beta`, Isozaki et al. 2010) を計算します。
  従来は語順相関のみを提供しており RIBES 本体は計算できませんでした。
  併せて `calc_brevity_penalty`、`calc_normalized_kendalls_tau`、
  `calc_word_orders` を追加しました。
- `lpu.data_structs.trees.TreeNode.fromS` が S 式を解析するように
  なりました (従来は引数を無視して空ノードを返していました)。
- フレーズ/ルールテーブル操作ツールの 5 コマンド。`main()` を持ちながら
  未登録で到達不能だったものです:
  `lpu-smt-convert-extract`、`lpu-smt-filter`、
  `lpu-smt-make-glue-rules`、`lpu-smt-normalize`、
  `lpu-smt-triangulate`。
- `tests/` 配下の pytest スイート (`test/` にあった assert の無い
  4 スクリプトを置き換え) と、テスト・リリース用の GitHub Actions
  ワークフロー。
- `README.ja.md` と本変更履歴。

### 修正

Python バージョンとは無関係に 0.2.x で壊れていたバグ:

- `common.config`: `_update_data` が `_conf=None` を拒否するため
  `Config.update(**kwargs)` が必ず例外になっていました。これにより
  `lpu-word-align-train` はどの Python でも動作しませんでした。
  同関数のエラーメッセージは `.format()` の呼び出しが漏れており、
  また `ConfigData` からの更新は `__main` をクラス属性として
  参照していたため失敗していました。
- `common.files`: `getContentSize()` が既に存在しない
  `gzip.read32()` を呼んでいたため常に `-1` を返し、gzip に対する
  進捗表示が無言で無効化されていました。`rawsize()` は 1 バイト
  少ない値を返していました。`is_gzipped()` はマジックナンバーを
  見る代わりに 1 行を解凍していました。
- `common.environ`: `get_env()` は `system=False` のときだけ
  `default` を返していたため、既定の引数では見つからない場合に
  `None` が返っていました。`StackHolder.unset()` は層内の他の変数の
  記録まで破棄していました。層が共有スタック `env_stack` に積まれた
  まま取り除かれていませんでした。
- `common.logging`: `using_config()` が `quiet` の代わりに `debug` を
  渡しており、さらに `get_quiet_status()` が `QUIET` を読む一方で
  `set_quiet()` は `LPU_QUIET` を設定していたため、quiet モードを
  有効にできませんでした。`LoggingConfig` は `unset_debug` を二重に
  定義していて後者が前者を隠していたため、後者を `unset_quiet` に
  改名しました。
- `common.progress`: `pipe_view()` が `outfunc` を stdout 出力の抑止
  フラグとしてしか使わず一度も呼び出していなかったため、内容が
  捨てられていました。
- `data_structs.trees`: `TreeNode.checkValid(deep=True)` が、再帰の
  条件式がコメントアウトされたまま `return False` だけ残っていたため、
  子を持つノードを全て不正と報告していました。
  `calcTreeEditDistance` の再帰本体に残っていたデバッグ用 `print()`
  も削除しました。
- `data_structs.trie`: `TwoWayIDMap.ids/items/keys` が C++ の
  `std::string` 要素を Python オブジェクトとして受けていたため、
  3 つとも `AttributeError` になっていました。`pycedar` 0.2 の
  dict 互換 API へ移行しました (0.2 で `num_keys()`、`predict()`、
  `erase()` が廃止されています)。`pycedar` 0.3.1 でも検証済みです。
- `metrics.ribes`: 語順対応付けにおいて、文脈窓の一致数を 1 ではなく
  2 と比較していた誤りと、参照文に無い語が `continue` ではなく
  無意味な `pass` を通過していた誤りを修正しました。
- Python 3 との非互換: `from collections import Iterable` (3.10 で削除)、
  Python 2 の名残である素の `long` 型名、`is` による文字列比較、
  不正なエスケープシーケンス。

### 削除

- コメントアウトされたコード 418 行 (全体の約 10%)。`.pxd` の宣言と
  重複する Cython 宣言コメント、コメントアウトされた `@cython`
  デコレータ、コメントアウトされたデバッグ出力と import、
  実コードと同一内容のコメントが対象です。

## 0.2.10 (2020-03-02)

これ以前のリリースについては git の履歴を参照してください。
