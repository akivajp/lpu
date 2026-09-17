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

import pytest

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