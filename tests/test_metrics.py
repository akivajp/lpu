
'''Tests for lpu.metrics

Expected values are computed by hand from the definitions of each metric,
so that the tests do not depend on any third-party implementation.

lpu.metrics のテスト。
期待値は各指標の定義から手計算しており、サードパーティ実装に依存しない。
'''

import itertools
import math
import random

import pytest

from lpu.metrics import bleu
from lpu.metrics import ranking
from lpu.metrics import ribes


class TestBleu:
    def test_ngram_precision_of_identical_sentences_is_one(self):
        words = 'the cat sat on the mat'.split()
        for n in range(1, 5):
            assert bleu.calc_ngram_precision(words, words, n) == 1.0

    def test_ngram_precision_counts_clipped_matches(self):
        ref = 'a b c d'.split()
        hyp = 'a b x y'.split()
        # unigram: a, b match out of 4 / ユニグラム: 4 語中 a, b が一致
        assert bleu.calc_ngram_precision(ref, hyp, 1) == 2 / 4
        # bigram: only "a b" matches out of 3 / バイグラム: 3 組中 "a b" のみ
        assert bleu.calc_ngram_precision(ref, hyp, 2) == 1 / 3

    def test_ngram_precision_is_zero_when_hypothesis_is_too_short(self):
        assert bleu.calc_ngram_precision('abc', 'a', 2) == 0.0

    def test_brevity_penalty(self):
        ref = 'a b c d'.split()
        assert bleu.calc_breavity_penalty(ref, ref) == 1.0
        # A longer hypothesis is not penalized / 長い仮説は減点しない
        assert bleu.calc_breavity_penalty(ref, [*ref, 'e']) == 1.0
        hyp = 'a b'.split()
        assert bleu.calc_breavity_penalty(ref, hyp) == pytest.approx(
            math.exp(1 - 4 / 2))

    def test_eval_bleu_of_identical_sentences_is_one(self):
        words = 'the cat sat on the mat'.split()
        assert bleu.eval_bleu(words, words, 4) == pytest.approx(1.0)

    def test_eval_bleu_is_zero_when_word_order_is_destroyed(self):
        ref = 'the cat sat on the mat'.split()
        hyp = list(reversed(ref))
        assert bleu.eval_bleu(ref, hyp, 4) == 0.0


class TestRibesWordOrders:
    '''Alignment of hypothesis words to reference ranks

    仮説語を参照文の順位へ対応付ける処理。
    '''

    def test_unique_words_align_directly(self):
        ref = 'a b c d'.split()
        hyp = 'c a d b'.split()
        assert ribes.calc_word_orders(hyp, ref) == [2, 0, 3, 1]

    def test_words_absent_from_the_reference_are_skipped(self):
        '''An unmatched word must be skipped, not silently ignored

        0.2.x wrote "pass" where "continue" was meant.

        参照文に無い語はスキップされること。
        0.2.x では "continue" のつもりで "pass" と書かれていた。
        '''
        ref = 'a b c'.split()
        hyp = 'a z c'.split()
        assert ribes.calc_word_orders(hyp, ref) == [0, 2]

    def test_ambiguous_words_are_resolved_by_left_context(self):
        '''A duplicated word is disambiguated by the preceding context

        0.2.x compared the left-context match count against 2 instead of 1,
        so this resolution never succeeded.

        重複語は直前の文脈で一意化されること。
        0.2.x は左文脈の一致数を 1 ではなく 2 と比較していたため、
        この解決が成功しなかった。
        '''
        ref = 'x a y a z'.split()
        hyp = 'x a y a z'.split()
        # Both occurrences of "a" must be aligned, at ranks 1 and 3
        # 2 つの "a" が順位 1 と 3 に対応付けられること
        assert ribes.calc_word_orders(hyp, ref) == [0, 1, 2, 3, 4]

    def test_returns_empty_for_a_completely_unrelated_hypothesis(self):
        assert ribes.calc_word_orders('xyz', 'abc') == []


class TestNormalizedKendallsTau:
    def test_ascending_order_is_one(self):
        assert ribes.calc_normalized_kendalls_tau([0, 1, 2, 3]) == 1.0

    def test_descending_order_is_zero(self):
        assert ribes.calc_normalized_kendalls_tau([3, 2, 1, 0]) == 0.0

    def test_single_element_is_one(self):
        assert ribes.calc_normalized_kendalls_tau([5]) == 1.0

    def test_empty_is_zero(self):
        assert ribes.calc_normalized_kendalls_tau([]) == 0.0

    def test_counts_every_ascending_pair(self):
        '''All pairs are counted, not only contiguous increasing runs

        [2, 0, 1, 3, 4, 5, 6] has 2 inversions out of 21 pairs, so the
        normalized tau is 19/21. Counting only contiguous increasing runs
        would give a different (smaller) value.

        連続する増加区間だけでなく全ペアを数えること。
        [2, 0, 1, 3, 4, 5, 6] は 21 ペア中 2 つが反転なので 19/21 となる。
        連続増加区間のみを数えると異なる (より小さい) 値になる。
        '''
        orders = [2, 0, 1, 3, 4, 5, 6]
        assert ribes.calc_normalized_kendalls_tau(orders) == pytest.approx(
            19 / 21)

    @pytest.mark.parametrize('seed', range(20))
    def test_matches_a_brute_force_count(self, seed):
        '''Cross-check against an independent brute-force implementation

        独立なブルートフォース実装との突き合わせ。
        '''
        rng = random.Random(seed)
        orders = [rng.randrange(0, 10) for _ in range(rng.randint(2, 9))]
        pairs = list(itertools.combinations(orders, 2))
        expected = sum(1 for a, b in pairs if a < b) / len(pairs)
        assert ribes.calc_normalized_kendalls_tau(orders) == pytest.approx(
            expected)


class TestEvalRibes:
    '''RIBES = NKT * P**alpha * BP**beta (Isozaki et al., 2010)'''

    def test_identical_sentences_score_one(self):
        words = 'the cat sat on the mat'.split()
        assert ribes.eval_ribes(words, words) == pytest.approx(1.0)

    def test_reversed_sentence_scores_zero(self):
        ref = 'a b c d e'.split()
        assert ribes.eval_ribes(ref, list(reversed(ref))) == 0.0

    def test_empty_hypothesis_scores_zero(self):
        assert ribes.eval_ribes('abc', '') == 0.0

    def test_unrelated_hypothesis_scores_zero(self):
        ref = 'the cat sat on the mat'.split()
        hyp = 'a dog ran through the park quickly'.split()
        assert ribes.eval_ribes(ref, hyp) == 0.0

    def test_matches_the_hand_computed_value_for_a_reordering(self):
        '''A single long-distance move is computed by hand

        ref ranks of the hypothesis are [2, 0, 1, 3, 4, 5, 6], so
        NKT = 19/21, P = 7/7 = 1 and BP = 1.

        語順が 1 箇所だけ離れて入れ替わる場合を手計算で検証する。
        仮説語の参照順位は [2, 0, 1, 3, 4, 5, 6] であり、
        NKT = 19/21, P = 7/7 = 1, BP = 1 となる。
        '''
        ref = 'I read a book yesterday at home'.split()
        hyp = 'a I read book yesterday at home'.split()
        assert ribes.calc_word_orders(hyp, ref) == [2, 0, 1, 3, 4, 5, 6]
        assert ribes.eval_ribes(ref, hyp) == pytest.approx(19 / 21)

    def test_applies_the_brevity_penalty_to_a_short_hypothesis(self):
        '''A truncated hypothesis keeps NKT = 1 but is penalized

        短い仮説は NKT = 1 のままでもペナルティを受けること。
        '''
        ref = 'the cat sat on the mat'.split()
        hyp = 'the cat sat'.split()
        orders = ribes.calc_word_orders(hyp, ref)
        nkt = ribes.calc_normalized_kendalls_tau(orders)
        precision = len(orders) / len(hyp)
        bp = min(1.0, math.exp(1.0 - len(ref) / len(hyp)))
        expected = nkt * precision ** 0.25 * bp ** 0.10
        assert ribes.eval_ribes(ref, hyp) == pytest.approx(expected)
        assert ribes.eval_ribes(ref, hyp) < 1.0

    def test_exponents_are_configurable(self):
        ref = 'a b c d'.split()
        hyp = 'a b'.split()
        default = ribes.eval_ribes(ref, hyp)
        no_penalty = ribes.eval_ribes(ref, hyp, alpha=0.0, beta=0.0)
        assert no_penalty > default

    def test_score_stays_within_the_unit_interval(self):
        rng = random.Random(0)
        words = list('abcdefg')
        for _ in range(200):
            ref = [rng.choice(words) for _ in range(rng.randint(1, 7))]
            hyp = [rng.choice(words) for _ in range(rng.randint(1, 7))]
            score = ribes.eval_ribes(ref, hyp)
            assert 0.0 <= score <= 1.0


class TestFindContext:
    def test_finds_every_occurrence(self):
        assert ribes.find_context(['a', 'b'], 'a b c a b'.split()) == [0, 3]

    def test_returns_empty_when_absent(self):
        assert ribes.find_context(['z'], 'a b c'.split()) == []


class TestRanking:
    def test_precision_at_k_counts_ranks_within_the_cut_off(self):
        # 3 件中 1 位と 2 位の 2 件が上位 2 件に入る
        assert ranking.calc_precision_at_k([1, 2, 5], 2) == 2 / 3

    def test_precision_at_k_of_a_perfect_ranking_is_one(self):
        assert ranking.calc_precision_at_k([1, 1, 1], 1) == 1.0

    def test_precision_at_k_counts_none_as_a_miss(self):
        # 未検出 (None) は打ち切り順位に関わらず不正解として数える
        assert ranking.calc_precision_at_k([1, None], 10) == 0.5

    def test_precision_at_k_rejects_a_non_positive_k(self):
        with pytest.raises(ValueError):
            ranking.calc_precision_at_k([1], 0)

    def test_mean_reciprocal_rank_averages_the_reciprocals(self):
        # (1/1 + 1/2 + 1/4) / 3
        assert ranking.calc_mean_reciprocal_rank([1, 2, 4]) == (1 + 0.5 + 0.25) / 3

    def test_mean_reciprocal_rank_of_a_perfect_ranking_is_one(self):
        assert ranking.calc_mean_reciprocal_rank([1, 1]) == 1.0

    def test_mean_reciprocal_rank_treats_none_as_zero(self):
        assert ranking.calc_mean_reciprocal_rank([1, None]) == 0.5

    @pytest.mark.parametrize('ranks', [[0], [-1]])
    def test_a_non_positive_rank_is_rejected(self, ranks):
        # 0 以下の順位は MRR で発散し P@k を歪めるため受け付けない
        with pytest.raises(ValueError):
            ranking.calc_mean_reciprocal_rank(ranks)
        with pytest.raises(ValueError):
            ranking.calc_precision_at_k(ranks, 1)

    @pytest.mark.parametrize('func', [
        ranking.calc_mean_reciprocal_rank,
        lambda ranks: ranking.calc_precision_at_k(ranks, 1),
    ])
    def test_an_empty_rank_sequence_is_rejected(self, func):
        # 空列では割合が定義できないため 0 除算ではなく ValueError とすること
        with pytest.raises(ValueError):
            func([])

    def test_mrr_never_exceeds_precision_at_one_plus_the_rest(self):
        # 定義上 MRR は P@1 以上 1 以下に収まること
        rng = random.Random(0)
        for _ in range(50):
            ranks = [rng.randint(1, 10) for _ in range(rng.randint(1, 8))]
            mrr = ranking.calc_mean_reciprocal_rank(ranks)
            assert ranking.calc_precision_at_k(ranks, 1) <= mrr <= 1.0
