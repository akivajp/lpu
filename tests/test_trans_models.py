# -*- coding: utf-8 -*-

'''Tests for the phrase/rule table operations (lpu.smt.trans_models)

The SMT table commands were registered as entry points in 0.3.0 but only
their --help output was tested. This module adds end-to-end coverage of
the actual processing, invoking the CLI in a subprocess like
test_commands.py does.

フレーズ/ルールテーブル操作のテスト。0.3.0 で entry point 登録された
これらのコマンドは --help の疎通しか検証されていなかったため、
test_commands.py と同じくサブプロセスで CLI を起動する end-to-end
テストをここに追加する。
'''

import gzip


from conftest import requires_trans_models


@requires_trans_models
class TestTriangulate:
    '''End-to-end triangulation of two pivot-sharing tables

    pivot 言語を共有する 2 つのテーブルの三角化 (pivot) の end-to-end テスト。
    '''

    # A Travatar rule line is:
    #   src ||| trg ||| features ||| counts ||| aligns
    # Feature values of keys of length >= 4 are natural-log encoded
    # (getTravatarFeatures applies e ** val), so egfp=-0.7 means p=0.4966.
    # Travatar 形式のルール行。長さ 4 以上のキーの値は自然対数で格納される。
    TABLE_SRC_PVT = (
        '"the" "cat" "sat" ||| "le" "chat" '
        '||| p=-0.9 egfp=-0.7 egfl=-0.6 fgep=-0.8 fgel=-0.5 w=3 '
        '||| 10 10 10 ||| 0-0 1-1 2-2\n'
    )
    TABLE_PVT_TRG = (
        '"le" "chat" ||| "die" "Katze" '
        '||| p=-0.9 egfp=-0.7 egfl=-0.4 fgep=-0.8 fgel=-0.3 w=2 '
        '||| 10 10 10 ||| 0-0 1-1\n'
    )

    def _run_pivot(self, tmp_path, table1, table2):
        from test_commands import run_command
        savefile = tmp_path / 'pivoted.txt'
        result = run_command('lpu.smt.trans_models.triangulate', [
            str(table1), str(table2), str(savefile),
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        return savefile

    def test_produces_the_pivoted_rule(self, tmp_path):
        '''The pivot phrase must be consumed and src/trg combined

        pivot フレーズが消費され、原言語と目標言語が結合されたルールが
        出力されること。
        '''
        table1 = tmp_path / 'table.src_pvt'
        table2 = tmp_path / 'table.pvt_trg'
        table1.write_text(self.TABLE_SRC_PVT, encoding='utf-8')
        table2.write_text(self.TABLE_PVT_TRG, encoding='utf-8')
        savefile = self._run_pivot(tmp_path, table1, table2)

        lines = savefile.read_text(encoding='utf-8').splitlines()
        assert lines, 'the pivoted table is empty'

        # The rule must connect the outer languages through the pivot
        # ルールは pivot 言語を介して外側の言語対を結ぶこと
        fields = [field.strip() for field in lines[0].split('|||')]
        assert fields[0] == '"the" "cat" "sat"'
        assert fields[1] == '"die" "Katze"'

    def test_multiplies_the_trans_probs(self, tmp_path):
        '''prodprob must multiply the forward probs of both sides

        prodprob 方式で両側の順方向確率が乗算されること。
        egfp: log(e^-0.7 * e^-0.7) = -1.4
        '''
        import math
        table1 = tmp_path / 'table.src_pvt'
        table2 = tmp_path / 'table.pvt_trg'
        table1.write_text(self.TABLE_SRC_PVT, encoding='utf-8')
        table2.write_text(self.TABLE_PVT_TRG, encoding='utf-8')
        savefile = self._run_pivot(tmp_path, table1, table2)

        line = savefile.read_text(encoding='utf-8').splitlines()[0]
        features = dict(
            pair.split('=', 1) for pair in line.split('|||')[2].split()
        )
        # log(p) values of length-4 keys are re-log-transformed by to_str
        # (to_str で長さ 4 以上のキーの値は対数へ戻される)
        expected = math.log(math.exp(-0.7) * math.exp(-0.7))
        assert abs(float(features['egfp']) - expected) < 1e-5
        assert abs(float(features['egfl']) - (-1.0)) < 1e-5

    def test_merges_alignments_through_the_pivot(self, tmp_path):
        '''Alignments must be chained src->pvt and pvt->trg

        単語アライメントが pivot を経由して src->trg に連結されること。
        src side 0-0,1-1,2-2 and trg side 0-0,1-1 give 0-0 and 1-1.
        '''
        table1 = tmp_path / 'table.src_pvt'
        table2 = tmp_path / 'table.pvt_trg'
        table1.write_text(self.TABLE_SRC_PVT, encoding='utf-8')
        table2.write_text(self.TABLE_PVT_TRG, encoding='utf-8')
        savefile = self._run_pivot(tmp_path, table1, table2)

        line = savefile.read_text(encoding='utf-8').splitlines()[0]
        aligns = line.split('|||')[4].strip().split()
        assert sorted(aligns) == ['0-0', '1-1']

    def test_gz_output(self, tmp_path):
        '''A .gz savefile must be written as gzip transparently

        保存先が .gz の場合は透過的に gzip で書き出されること。
        '''
        table1 = tmp_path / 'table.src_pvt'
        table2 = tmp_path / 'table.pvt_trg'
        table1.write_text(self.TABLE_SRC_PVT, encoding='utf-8')
        table2.write_text(self.TABLE_PVT_TRG, encoding='utf-8')
        savefile = tmp_path / 'pivoted.txt.gz'
        from test_commands import run_command
        result = run_command('lpu.smt.trans_models.triangulate', [
            str(table1), str(table2), str(savefile),
        ], cwd=str(tmp_path))
        assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
        with gzip.open(savefile, 'rt', encoding='utf-8') as fobj:
            lines = fobj.read().splitlines()
        assert lines
        assert '"die" "Katze"' in lines[0]


def _run(module, args, cwd):
    '''Invoke a table command in a subprocess and return its stdout lines

    テーブル操作コマンドをサブプロセスで起動し、標準出力を行のリスト
    で返す。失敗時はテストを即座に失敗させる。
    '''
    from test_commands import run_command
    result = run_command(module, args, cwd=str(cwd))
    assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')
    return result


def _parse_features(field):
    '''Parse a "k=v k=v" feature field into a dict

    "k=v k=v" 形式の feature フィールドを辞書へ変換する。
    '''
    return dict(pair.split('=', 1) for pair in field.split())


@requires_trans_models
class TestFilter:
    '''Filtering a Travatar table by count rules and n-best

    出現回数によるルールと n-best 制限でのテーブルフィルタのテスト。
    '''

    # counts field order is: cooc src trg (TravatarRecord.loadLine)
    # (counts フィールドの並びは cooc src trg)
    TABLE = (
        '"a" ||| "x" ||| egfp=-1.2 ||| 3 2 1 ||| 0-0\n'
        '"a" ||| "y" ||| egfp=-0.3 ||| 8 2 1 ||| 0-0\n'
        '"b" ||| "z" ||| egfp=-0.3 ||| 1 2 1 ||| 0-0\n'
    )

    def _run_filter(self, tmp_path, *extra_args):
        table = tmp_path / 'table.txt'
        table.write_text(self.TABLE, encoding='utf-8')
        savefile = tmp_path / 'filtered.txt'
        _run('lpu.smt.trans_models.filter',
             [str(table), str(savefile)] + list(extra_args), tmp_path)
        return savefile.read_text(encoding='utf-8').splitlines()

    def test_keeps_only_records_passing_the_count_rule(self, tmp_path):
        '''c.c > 2 must drop the record with cooc = 1

        c.c > 2 により cooc = 1 のレコードが除外されること。
        '''
        lines = self._run_filter(tmp_path, 'c.c > 2')
        assert [line.split(' ||| ')[0] for line in lines] == ['"a"', '"a"']
        assert [line.split(' ||| ')[1] for line in lines] == ['"x"', '"y"']

    def test_nbest_keeps_the_best_target_per_source(self, tmp_path):
        '''--nbest must keep the highest egfp target of each source

        --nbest で各原言語側の egfp 最大の目標言語だけが残ること。
        egfp は対数で格納されるため、e**-0.3 > e**-1.2 で "y" が上位。
        '''
        lines = self._run_filter(tmp_path, 'c.c > 0', '--nbest', '1')
        assert lines[0].split(' ||| ')[1] == '"y"'
        # The other source still keeps its single record
        # (もう一方の原言語側のレコードはそのまま残る)
        assert any(line.split(' ||| ')[0] == '"b"' for line in lines)


@requires_trans_models
class TestNormalize:
    '''Probability normalization of a Travatar table

    Travatar テーブルの確率正規化のテスト。egfp は同一原言語内の
    目標言語で、fgep は同一目標言語内の原言語で正規化される。
    '''

    # Feature values of length-4 keys are natural-log encoded on load, so
    # egfp=-0.693147 is p=0.5, etc. Input probabilities:
    #   ("a" -> "x"): egfp 0.5, fgep 0.5
    #   ("a" -> "y"): egfp 0.25, fgep 0.4
    #   ("b" -> "x"): egfp 0.3, fgep 0.5
    TABLE = (
        '"a" ||| "x" ||| egfp=-0.693147 fgep=-0.693147 '
        '||| 10 10 10 ||| 0-0\n'
        '"a" ||| "y" ||| egfp=-1.386294 fgep=-0.916291 '
        '||| 10 10 10 ||| 0-0\n'
        '"b" ||| "x" ||| egfp=-1.203973 fgep=-0.693147 '
        '||| 10 10 10 ||| 0-0\n'
    )

    def test_normalizes_the_directional_probabilities(self, tmp_path):
        '''egfp/fgep must become conditional probs p(trg|src) and p(src|trg)

        egfp/fgep が条件付き確率 p(trg|src) / p(src|trg) へ正規化される
        こと (出力では再び自然対数で格納される)。
        '''
        import math
        table = tmp_path / 'table.txt'
        table.write_text(self.TABLE, encoding='utf-8')
        savefile = tmp_path / 'normalized.txt'
        _run('lpu.smt.trans_models.normalize',
             [str(table), str(savefile)], tmp_path)

        records = []
        for line in savefile.read_text(encoding='utf-8').splitlines():
            fields = [field.strip() for field in line.split(' ||| ')]
            records.append((fields[0], fields[1],
                            _parse_features(fields[2])))
        assert [r[0] for r in records] == ['"a"', '"a"', '"b"']

        # src_total("a") = 0.5 + 0.25 = 0.75
        assert abs(float(records[0][2]['egfp'])
                   - math.log(0.5 / 0.75)) < 1e-4
        assert abs(float(records[1][2]['egfp'])
                   - math.log(0.25 / 0.75)) < 1e-4
        # src_total("b") = 0.3, so egfp becomes p = 1
        assert abs(float(records[2][2]['egfp'])) < 1e-4

        # trg_total("x") = 0.5 + 0.5 = 1.0, trg_total("y") = 0.4
        assert abs(float(records[0][2]['fgep'])
                   - math.log(0.5 / 1.0)) < 1e-4
        assert abs(float(records[1][2]['fgep'])) < 1e-4
        assert abs(float(records[2][2]['fgep'])
                   - math.log(0.5 / 1.0)) < 1e-4


@requires_trans_models
class TestMakeGlueRules:
    '''Glue rule extraction from a Travatar table

    Travatar テーブルからの glue ルール生成のテスト。
    '''

    TABLE = (
        # a general tag rule: symbols[-2] == "@" -> tag NP
        '"cat" "sat" @ NP ||| "cat" "sat" ||| glue=1 ||| 5 5 5 ||| 0-0\n'
        # single word rules with a quoted word: POS tags N and DT
        '"cat" @ N ||| "cat" ||| unk=1 ||| 5 5 5 ||| 0-0\n'
        '"the" @ DT ||| "the" ||| unk=1 ||| 5 5 5 ||| 0-0\n'
        # a plain terminal rule contributes no tag
        '"the" "cat" ||| "le" "chat" ||| p=-0.5 ||| 2 2 2 ||| 0-0 1-1\n'
        # the sentence tag S must not produce a glue rule itself
        'x0:S @ S ||| x0:S @ S ||| glue=1 ||| 5 5 5 ||| 0-0\n'
    )

    def test_extracts_the_expected_glue_rules(self, tmp_path):
        '''Tags S/X and the final combination rule must be handled

        タグ S と X の扱い、および末尾の結合ルールが期待どおり生成される
        こと。行の集合として比較する (set の反復順はハッシュに依存する)。
        '''
        table = tmp_path / 'table.txt'
        table.write_text(self.TABLE, encoding='utf-8')
        savefile = tmp_path / 'glue-rules.txt'
        _run('lpu.smt.trans_models.make_glue_rules',
             [str(table), str(savefile)], tmp_path)

        lines = set(savefile.read_text(encoding='utf-8').splitlines())
        expected = {
            # every tag except S gets an S-target glue rule
            'x0:NP @ S ||| x0:NP @ S ||| glue=1',
            'x0:X @ S ||| x0:X @ S ||| glue=1',
            # POS tags get the unk-carrying X-target rules
            'x0:X @ N ||| x0:X @ N ||| glue=1 unk=1',
            'x0:X @ DT ||| x0:X @ DT ||| glue=1 unk=1',
            # plus the final X combination rule
            'x0:X x1:X @ X ||| x0:X x1:X @ X ||| glue=1 unk=1',
        }
        assert lines == expected


@requires_trans_models
class TestConvertExtract:
    '''Conversion of an extract file into a Travatar rule table

    extract ファイルから Travatar ルールテーブルへの変換のテスト。
    '''

    def test_keeps_terminal_rules_unchanged(self, tmp_path):
        '''A terminal-only extract line must pass through as-is

        端末記号のみの行はそのまま出力されること。
        '''
        src = tmp_path / 'extract.txt'
        src.write_text('"the" "cat" ||| "le" "chat" ||| 10 ||| 0-0 1-1\n',
                       encoding='utf-8')
        savefile = tmp_path / 'converted.txt'
        _run('lpu.smt.trans_models.convert_extract',
             [str(src), str(savefile)], tmp_path)
        assert savefile.read_text(encoding='utf-8').splitlines() == [
            '"the" "cat" ||| "le" "chat" ||| 10 ||| 0-0 1-1',
        ]

    def test_renumbers_the_variables(self, tmp_path):
        '''Non-terminal variables must be renumbered from 0 in order

        非終端記号変数は出現順に x0 から採番し直されること。
        '''
        src = tmp_path / 'extract.txt'
        src.write_text('x1:X "the" ||| "le" x1:X ||| 5 ||| 1-0\n',
                       encoding='utf-8')
        savefile = tmp_path / 'converted.txt'
        _run('lpu.smt.trans_models.convert_extract',
             [str(src), str(savefile)], tmp_path)
        assert savefile.read_text(encoding='utf-8').splitlines() == [
            'x0:X "the" ||| "le" x0:X ||| 5 ||| 1-0',
        ]

    def test_reverse_swaps_the_direction(self, tmp_path):
        '''--reverse must swap src/trg and mirror the alignments

        --reverse で src/trg が入れ替わり、アライメントも反転されること。
        '''
        src = tmp_path / 'extract.txt'
        src.write_text('"le" "chat" ||| "the" "cat" ||| 8 ||| 0-1 1-0\n',
                       encoding='utf-8')
        savefile = tmp_path / 'converted.txt'
        _run('lpu.smt.trans_models.convert_extract',
             ['--reverse', str(src), str(savefile)], tmp_path)
        assert savefile.read_text(encoding='utf-8').splitlines() == [
            '"the" "cat" ||| "le" "chat" ||| 8 ||| 0-1 1-0',
        ]

    def test_no_unary_skips_terminal_free_rules(self, tmp_path):
        '''--no-unary must drop rules without any terminal symbol

        --no-unary で端末記号を含まない (unary cycle の原因になる) ルール
        が除外されること。
        '''
        src = tmp_path / 'extract.txt'
        src.write_text(
            'x0:X ||| X ||| 3 ||| 0-0\n'
            '"cat" x0:X ||| x0:X "chat" ||| 3 ||| 0-0\n',
            encoding='utf-8')
        savefile = tmp_path / 'converted.txt'
        _run('lpu.smt.trans_models.convert_extract',
             ['--no-unary', str(src), str(savefile)], tmp_path)
        lines = savefile.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 1
        assert lines[0].startswith('"cat" x0:X')