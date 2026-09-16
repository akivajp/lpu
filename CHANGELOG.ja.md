# 変更履歴

English version is available in [CHANGELOG.md](CHANGELOG.md).

## 0.3.0 (未リリース)

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
