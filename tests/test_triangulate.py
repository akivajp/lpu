# -*- coding: utf-8 -*-

'''Tests for lpu.smt.trans_models.triangulate

lpu.smt.trans_models.triangulate のテスト。
2 つのフレーズ/ルールテーブルを共通のピボット句で統合する
triangulation 処理を、ユニット (特徴量・カウント更新) と
エンドツーエンド (pivot()) の両面から検証する。
'''

import math

import pytest

from lpu.smt.trans_models import triangulate
from lpu.smt.trans_models.records import MosesRecord


def _moses(src, trg, features='0 0 0 0', counts='0 0 0', aligns=''):
    '''Build a MosesRecord from its fields

    Feature order is fgep fgel egfp egfl, count order is trg src cooc.
    (特徴量は fgep fgel egfp egfl の順、カウントは trg src cooc の順)
    '''
    return MosesRecord(' ||| '.join([src, trg, features, aligns, counts]))


class TestUpdateFeatures:
    def test_prodprob_multiplies_scores(self, tmp_path):
        '''p(src,trg) ~ p(pvt|src) * p(trg|pvt), so every score is a product

        prodprob は確率の積を取る (src→pvt と pvt→trg の同時確率)。
        '''
        workset = triangulate.WorkSet(str(tmp_path / 'out.txt'),
                                      str(tmp_path), 'prodprob',
                                      matchMethod='hiero')
        src = _moses('a', 'x', '1 0.5 1 0.5', '0 4 0', '0-0')
        trg = _moses('x', 'b', '1 0.5 1 0.5', '0 3 0', '0-0')
        recPivot = _moses('a', 'b')
        try:
            triangulate.updateFeatures(recPivot, (src, trg), workset)
        finally:
            workset.close()
        features = recPivot.features
        assert features['egfp'] == pytest.approx(1 * 1)
        assert features['egfl'] == pytest.approx(0.5 * 0.5)
        assert features['fgep'] == pytest.approx(1 * 1)
        assert features['fgel'] == pytest.approx(0.5 * 0.5)

    def test_prodprob_multi_target_keeps_the_pivot_features(self, tmp_path):
        workset = triangulate.WorkSet(str(tmp_path / 'out.txt'),
                                      str(tmp_path), 'prodprob',
                                      matchMethod='hiero',
                                      multi_target=True)
        src = _moses('a', 'x', '1 0.5 1 0.5', '0 4 0', '0-0')
        trg = _moses('x', 'b', '1 0.5 1 0.5', '0 3 0', '0-0')
        recMulti = _moses('a', 'b |COL| x')
        try:
            triangulate.updateFeatures(recMulti, (src, trg), workset,
                                       multi_target=True)
        finally:
            workset.close()
        features = recMulti.features
        # p(trg,pvt|src) ~ p(trg|pvt) * p(pvt|src)
        assert features['egfp'] == pytest.approx(1.0)
        # memoryless joint: p(src|pvt,trg) ~ f(src|pvt)
        assert features['fgep'] == pytest.approx(src.features['fgep'])
        # the src-pvt features are copied under the "1" prefix
        for key in ['egfl', 'egfp', 'fgel', 'fgep']:
            assert features['1' + key] == src.features[key]

    def test_weights_only_method_multiplies_lexical_weights(self, tmp_path):
        workset = triangulate.WorkSet(str(tmp_path / 'out.txt'),
                                      str(tmp_path), 'countmin')
        src = _moses('a', 'x', '1 0.5 1 0.5', '0 4 0')
        trg = _moses('x', 'b', '1 0.5 1 0.5', '0 3 0')
        recPivot = _moses('a', 'b')
        try:
            triangulate.updateFeatures(recPivot, (src, trg), workset)
        finally:
            workset.close()
        # only the lexical weights are multiplied
        # (語彙重みのみが乗算される)
        assert recPivot.features['egfl'] == pytest.approx(0.25)
        assert recPivot.features['fgel'] == pytest.approx(0.25)
        assert recPivot.features.get('egfp', 0) == 0

    def test_each_match_method_multiplies_the_scores(self, tmp_path):
        for match_method in ['hiero', 'symbols', 'treecomp']:
            workset = triangulate.WorkSet(str(tmp_path / 'out.txt'),
                                          str(tmp_path), 'prodprob',
                                          matchMethod=match_method)
            src = _moses('a', 'x', '2 1 2 1', '0 4 0')
            trg = _moses('x', 'b', '3 1 3 1', '0 3 0')
            recPivot = _moses('a', 'b')
            try:
                triangulate.updateFeatures(recPivot, (src, trg), workset)
            finally:
                workset.close()
            assert recPivot.features['egfp'] == pytest.approx(6.0)

    def test_invalid_match_method_raises(self, tmp_path):
        workset = triangulate.WorkSet(str(tmp_path / 'out.txt'),
                                      str(tmp_path), 'prodprob',
                                      matchMethod='unknown')
        src = _moses('a', 'x', '1 1 1 1', '0 4 0')
        trg = _moses('x', 'b', '1 1 1 1', '0 3 0')
        recPivot = _moses('a', 'b')
        try:
            with pytest.raises(AssertionError):
                triangulate.updateFeatures(recPivot, (src, trg), workset)
        finally:
            workset.close()

    def test_target_word_weight_is_copied(self, tmp_path):
        workset = triangulate.WorkSet(str(tmp_path / 'out.txt'),
                                      str(tmp_path), 'prodprob')
        src = _moses('a', 'x', '1 1 1 1', '0 4 0')
        trg = _moses('x', 'b', '1 1 1 1', '0 3 0')
        trg.features['w'] = 2
        src.features['w'] = 3
        recPivot = _moses('a', 'b')
        try:
            triangulate.updateFeatures(recPivot, (src, trg), workset)
        finally:
            workset.close()
        assert recPivot.features['w'] == 2


class TestUpdateCounts:
    def test_countmin_takes_the_minimum_cooccurrence(self, tmp_path):
        src = _moses('a', 'x', '0 0 0 0', '0 0 3')
        trg = _moses('x', 'b', '0 0 0 0', '0 0 5')
        recPivot = _moses('a', 'b', counts='0 0 2')
        triangulate.updateCounts(recPivot, (src, trg), 'countmin')
        assert recPivot.counts.cooc == pytest.approx(2 + 3)

    def test_bidirmin_combines_both_directions(self, tmp_path):
        # co1 = cooc1*cooc2/src2, co2 = cooc2*cooc1/trg1
        src = _moses('a', 'x', '0 0 0 0', '0 0 6', )  # cooc 6, trg 3
        src.counts.trg = 3
        trg = _moses('x', 'b', '0 0 0 0', '0 0 4')
        trg.counts.src = 4
        recPivot = _moses('a', 'b')
        triangulate.updateCounts(recPivot, (src, trg), 'bidirmin')
        assert recPivot.counts.cooc == pytest.approx(min(6 * 4 / 4,
                                                         4 * 6 / 3))

    def test_bidirgmean_takes_the_geometric_mean(self, tmp_path):
        src = _moses('a', 'x', '0 0 0 0', '0 0 6')
        src.counts.trg = 3
        trg = _moses('x', 'b', '0 0 0 0', '0 0 4')
        trg.counts.src = 4
        recPivot = _moses('a', 'b')
        triangulate.updateCounts(recPivot, (src, trg), 'bidirgmean')
        co1 = 6 * 4 / 4
        co2 = 4 * 6 / 3
        assert recPivot.counts.cooc == pytest.approx(math.sqrt(co1 * co2))

    def test_bidirmax_takes_the_maximum(self, tmp_path):
        src = _moses('a', 'x', '0 0 0 0', '0 0 6')
        src.counts.trg = 3
        trg = _moses('x', 'b', '0 0 0 0', '0 0 4')
        trg.counts.src = 4
        recPivot = _moses('a', 'b')
        triangulate.updateCounts(recPivot, (src, trg), 'bidirmax')
        assert recPivot.counts.cooc == pytest.approx(max(6, 8))

    def test_bidiravr_takes_the_average(self, tmp_path):
        src = _moses('a', 'x', '0 0 0 0', '0 0 6')
        src.counts.trg = 3
        trg = _moses('x', 'b', '0 0 0 0', '0 0 4')
        trg.counts.src = 4
        recPivot = _moses('a', 'b')
        triangulate.updateCounts(recPivot, (src, trg), 'bidiravr')
        assert recPivot.counts.cooc == pytest.approx((6 + 8) * 0.5)

    def test_prodprob_estimates_counts_from_the_probabilities(self, tmp_path):
        workset = triangulate.WorkSet(str(tmp_path / 'out.txt'),
                                      str(tmp_path), 'prodprob')
        src = _moses('a', 'x', '1 0.5 1 0.5', '0 4 0')
        trg = _moses('x', 'b', '1 0.5 1 0.5', '0 3 0')
        recPivot = _moses('a', 'b')
        try:
            triangulate.updateFeatures(recPivot, (src, trg), workset)
            triangulate.updateCounts(recPivot, (src, trg), 'prodprob')
        finally:
            workset.close()
        counts = recPivot.counts
        assert counts.src == pytest.approx(4)
        assert counts.cooc == pytest.approx(4 * 1)
        assert counts.trg == pytest.approx(4 * 1 / 1)

    def test_multi_accumulates_the_minimum(self, tmp_path):
        src = _moses('a', 'x', '0 0 0 0', '0 0 3')
        trg = _moses('x', 'b', '0 0 0 0', '0 0 5')
        recPivot = _moses('a', 'b', counts='0 0 2')
        triangulate.updateCounts(recPivot, (src, trg), 'multi')
        assert recPivot.counts.cooc == pytest.approx(2 + 3)

    def test_invalid_method_raises(self):
        recPivot = _moses('a', 'b')
        src = _moses('a', 'x', '0 0 0 0', '0 0 1')
        trg = _moses('x', 'b', '0 0 0 0', '0 0 1')
        with pytest.raises(AssertionError):
            triangulate.updateCounts(recPivot, (src, trg), 'unknown')


class TestMergeAligns:
    def test_alignments_are_composed_through_the_pivot(self):
        recPivot = _moses('a b', 'c d')
        recSrcPvt = _moses('a b', 'x y', aligns='0-0 1-1')
        recPvtTrg = _moses('x y', 'c d', aligns='0-1 1-0')
        triangulate.mergeAligns(recPivot, (recSrcPvt, recPvtTrg))
        assert recPivot.aligns == {'0-1', '1-0'}

    def test_unaligned_pivot_words_drop_out(self):
        recPivot = _moses('a', 'c')
        recSrcPvt = _moses('a', 'x', aligns='0-0')
        recPvtTrg = _moses('x', 'c', aligns='')
        triangulate.mergeAligns(recPivot, (recSrcPvt, recPvtTrg))
        assert recPivot.aligns == set()


class TestFilterByCountRatioToMax:
    def test_filters_list_records(self):
        records = [_moses('a', 'x', counts='0 0 100'),
                   _moses('a', 'y', counts='0 0 50'),
                   _moses('a', 'z', counts='0 0 1')]
        filtered = triangulate.filterByCountRatioToMax(records, div=10)
        # only the records with co >= 100/10 survive
        # (co が最大値の 1/10 未満のレコードは除外される)
        assert [r.trg for r in filtered] == ['x', 'y']

    def test_filters_dict_records(self):
        records = {'x': _moses('a', 'x', counts='0 0 100'),
                   'z': _moses('a', 'z', counts='0 0 1')}
        filtered = triangulate.filterByCountRatioToMax(records, div=10)
        assert list(filtered.keys()) == ['x']


class TestFlattenRecords:
    def test_dict_values_are_returned(self):
        records = {'b': 2, 'a': 1}
        assert sorted(triangulate.flattenRecords(records)) == [1, 2]

    def test_sorted_dict_returns_key_order(self):
        records = {'b': 'B', 'a': 'A'}
        assert list(triangulate.flattenRecords(records, sort=True)) == ['A',
                                                                        'B']

    def test_lists_are_returned_as_is(self):
        assert triangulate.flattenRecords([3, 1]) == [3, 1]

    def test_invalid_type_raises(self):
        with pytest.raises(AssertionError):
            triangulate.flattenRecords('text')


class TestPhraseTransProbs:
    def test_calc_src_count_sums_cooccurrences(self):
        records = {'a': _moses('s', 'a', counts='0 0 3'),
                   'b': _moses('s', 't', counts='0 0 1')}
        assert triangulate.calcSrcCount(records) == 4

    def test_forward_probs_are_cooccurrence_over_source_count(self):
        records = {'a': _moses('s', 'x', counts='0 0 3'),
                   'b': _moses('s', 'y', counts='0 0 1')}
        triangulate.calcPhraseTransProbsByCounts(records)
        recs = dict(records)
        assert recs['a'].counts.src == 4
        assert recs['a'].features['egfp'] == pytest.approx(0.75)
        assert recs['b'].features['egfp'] == pytest.approx(0.25)

    def test_trans_probs_are_recalculated_per_source_group(self, tmp_path):
        table = tmp_path / 'table.txt'
        table.write_text(
            'src1 ||| t1 ||| 0 0 0 0 ||| ||| 0 0 3\n'
            'src1 ||| t2 ||| 0 0 0 0 ||| ||| 0 0 1\n'
            'src2 ||| t3 ||| 0 0 0 0 ||| ||| 0 0 2\n',
            encoding='utf-8')
        out = tmp_path / 'probs.txt'
        triangulate.calcPhraseTransProbsOnTable(str(table), str(out))
        recs = {}
        for line in out.read_text(encoding='utf-8').strip().splitlines():
            rec = MosesRecord(line)
            recs[(rec.src, rec.trg)] = rec
        assert recs[('src1', 't1')].features['egfp'] == pytest.approx(0.75)
        assert recs[('src1', 't2')].features['egfp'] == pytest.approx(0.25)
        assert recs[('src2', 't3')].features['egfp'] == pytest.approx(1.0)


class TestWriteRecords:
    def test_writes_records_with_positive_counts_only(self, tmp_path):
        out = tmp_path / 'out.txt'
        records = {'x': _moses('a', 'x', counts='0 0 5'),
                   'y': _moses('a', 'y', counts='0 0 0')}
        with open(str(out), 'w', encoding='utf-8') as f_obj:
            triangulate.writeRecords(f_obj, records)
        text = out.read_text(encoding='utf-8')
        assert 'a ||| x' in text
        assert 'a ||| y' not in text


class _FakeLexCounts:
    '''A minimal stand-in for the word pair counts holder

    単語ペアカウント保持クラスの最小限の代替実装。
    '''
    def __init__(self):
        self.srcCounts = {'NULL': 2}
        self.trgCounts = {'NULL': 2}

    def calcLexProb(self, src_term, trg_term):
        return {'a': {'x': 0.4, 'y': 0.2}}.get(src_term, {}).get(trg_term,
                                                                 0.1)

    def calcLexProbRev(self, src_term, trg_term):
        # calcLexWeight passes (trg term, src term) for the reverse lookup
        # (逆向きの参照では calcLexWeight が (trg, src) の順で渡す)
        return {'a': {'x': 0.4}}.get(src_term, {}).get(trg_term, 0.05)


class TestCalcLexWeight:
    def test_forward_weight_multiplies_word_probs(self):
        lex_counts = _FakeLexCounts()
        rec = _moses('a', 'x y', aligns='0-0')
        # for forward probs the alignment map is read reversed
        # (順方向の重みでは逆方向のアラインメントマップを使う)
        weight = triangulate.calcLexWeight(rec, lex_counts, reverse=False)
        # aligned 'a'->'x' gives 0.4, the unaligned 'y' falls back to
        # calcLexProb('NULL', 'y') = 0.1
        assert weight == pytest.approx(0.4 * 0.1)

    def test_reverse_weight_uses_the_reversed_lookup(self):
        lex_counts = _FakeLexCounts()
        rec = _moses('a', 'x y', aligns='0-0')
        weight = triangulate.calcLexWeight(rec, lex_counts, reverse=True)
        assert weight == pytest.approx(0.4)

    def test_small_probabilities_are_clamped_to_the_minimum(self):
        lex_counts = _FakeLexCounts()
        rec = _moses('a', 'x', aligns='')
        # calcLexProb returns 0.1, far above MINPROB; a NULL lookup with a
        # tiny probability must be clamped to 10 ** -10
        lex_counts.calcLexProb = lambda src, trg: 10 ** -20
        weight = triangulate.calcLexWeight(rec, lex_counts, reverse=False)
        assert weight == pytest.approx(10 ** -10)


class TestCalcLexWeights:
    def test_writes_lexical_weights_into_the_table(self, tmp_path):
        table = tmp_path / 'table.txt'
        table.write_text('a ||| x y ||| 0 0 0 0 ||| 0-0 ||| 0 0 1\n',
                         encoding='utf-8')
        out = tmp_path / 'weighted.txt'
        triangulate.calcLexWeights(str(table), _FakeLexCounts(), str(out))
        text = out.read_text(encoding='utf-8')
        rec = MosesRecord(text)
        # forward: aligned 0.4 * unaligned 0.1; backward: the 'a' side
        # is aligned, so only the aligned lookup 0.4 applies
        # (順方向は整列 0.4 * 非整列 0.1。逆方向は 'a' 側が整列済みの
        #  ため、整列参照の 0.4 のみが適用される)
        assert rec.features['egfl'] == pytest.approx(0.4 * 0.1)
        assert rec.features['fgel'] == pytest.approx(0.4)

    def test_multi_target_records_use_the_col_features(self, tmp_path):
        table = tmp_path / 'table.txt'
        table.write_text('a ||| x |COL| s ||| 0 0 0 0 ||| 0-0 ||| 0 0 1\n',
                         encoding='utf-8')
        out = tmp_path / 'weighted.txt'
        triangulate.calcLexWeights(str(table), _FakeLexCounts(), str(out))
        text = out.read_text(encoding='utf-8')
        # the |COL| branch writes 0egfl / 0fgel features, which
        # MosesRecord.to_str does not serialize (only the 4 standard
        # features are); the record itself round-trips unchanged
        # (|COL| 分岐では 0egfl / 0fgel が計算されるが、MosesRecord.to_str
        #  は標準 4 特徴量しか出力しないため、レコード自体はそのまま
        #  往復する)
        rec = MosesRecord(text)
        assert '|COL|' in rec.trg
        assert rec.counts.cooc == pytest.approx(1)


class TestPivot:
    def _write_table(self, path, lines):
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    def test_pivot_combines_two_tables_through_the_pivot(self, tmp_path):
        table1 = tmp_path / 'src_pvt.txt'
        table2 = tmp_path / 'pvt_trg.txt'
        out = tmp_path / 'pivoted.txt'
        log = tmp_path / 'log.txt'
        # Moses feature order is fgep fgel egfp egfl; all probabilities
        # are 1 so the pivoted products are 1.
        # (Moses 形式の特徴量は fgep fgel egfp egfl の順。すべて確率 1
        #  なので、ピボット後の積も 1 になる)
        self._write_table(table1, [
            'a b ||| x y ||| 1 1 1 1 ||| 0-0 1-1 ||| 2 4 6',
        ])
        self._write_table(table2, [
            'x y ||| c d ||| 1 1 1 1 ||| 0-1 1-0 ||| 3 5 2',
        ])
        triangulate.pivot(str(table1), str(table2), savefile=str(out),
                          workdir=str(tmp_path), progress=False,
                          matchmethod='symbols', method='prodprob',
                          log=str(log))
        lines = out.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1
        rec = MosesRecord(lines[0])
        assert rec.src == 'a b'
        assert rec.trg == 'c d'
        # p(pvt|src) * p(trg|pvt) = 1 * 1
        assert rec.features['egfp'] == pytest.approx(1.0)
        counts = rec.counts
        assert counts.src == pytest.approx(4)
        assert counts.cooc == pytest.approx(4)
        assert counts.trg == pytest.approx(4)
        assert rec.aligns == {'0-1', '1-0'}
        log_text = log.read_text(encoding='utf-8')
        assert 'numRecSrcPvt = 1' in log_text
        assert 'numRecPvtTrg = 1' in log_text
        assert 'numRecSrcTrg = 1' in log_text

    def test_pivot_keeps_only_the_nbest_records(self, tmp_path):
        table1 = tmp_path / 'src_pvt.txt'
        table2 = tmp_path / 'pvt_trg.txt'
        out = tmp_path / 'pivoted.txt'
        self._write_table(table1, [
            'a ||| x ||| 1 1 1 1 ||| 0-0 ||| 0 2 0',
        ])
        self._write_table(table2, [
            'x ||| c ||| 1 1 1 1 ||| 0-0 ||| 0 2 0',
            'x ||| e ||| 1 1 1 1 ||| 0-0 ||| 0 2 0',
        ])
        triangulate.pivot(str(table1), str(table2), savefile=str(out),
                          workdir=str(tmp_path), progress=False,
                          matchmethod='symbols', method='prodprob',
                          nbest=1)
        lines = out.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1
        assert lines[0].split(' ||| ')[1] in ('c', 'e')

    def test_pivot_skips_symbol_mismatches(self, tmp_path):
        table1 = tmp_path / 'src_pvt.txt'
        table2 = tmp_path / 'pvt_trg.txt'
        out = tmp_path / 'pivoted.txt'
        # the pivot phrases share no symbol, so nothing is triangulated
        # (ピボット句の記号が一致しないため、何も統合されない)
        self._write_table(table1, [
            'a ||| x ||| 1 1 1 1 ||| 0-0 ||| 0 2 0',
        ])
        self._write_table(table2, [
            'z ||| c ||| 1 1 1 1 ||| 0-0 ||| 0 2 0',
        ])
        triangulate.pivot(str(table1), str(table2), savefile=str(out),
                          workdir=str(tmp_path), progress=False,
                          matchmethod='symbols', method='prodprob')
        assert out.read_text(encoding='utf-8') == ''