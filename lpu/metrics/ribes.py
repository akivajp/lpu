# -*- coding: utf-8 -*-

'''Functions to evaluate RIBES scores

RIBES (Rank-based Intuitive Bilingual Evaluation Score) is a metric for
distant language pairs proposed by Isozaki et al. (2010), defined as::

    RIBES = NKT * (P ** alpha) * (BP ** beta)

where NKT is the normalized Kendall's tau of the word rank order, P is the
unigram precision, and BP is the brevity penalty. The default exponents are
alpha=0.25 and beta=0.10, following the original paper.

RIBES (Rank-based Intuitive Bilingual Evaluation Score) スコアを計算する。
Isozaki et al. (2010) が遠い言語対向けに提案した評価尺度で、
語順の正規化 Kendall's tau (NKT)、ユニグラム精度 (P)、短さペナルティ (BP)
の積として定義される。既定の指数 alpha=0.25, beta=0.10 は原論文に従う。

Note: up to 0.2.x this module provided only `calc_kendalls_tau`, so RIBES
itself could not be computed. `eval_ribes` was added in 0.3.0.

注意: 0.2.x までは `calc_kendalls_tau` のみで RIBES 本体は計算できなかった。
`eval_ribes` は 0.3.0 で追加された。
'''

from collections.abc import Sequence
from itertools import combinations
import math

# Default exponents of the original paper / 原論文における既定の指数
DEFAULT_ALPHA = 0.25
DEFAULT_BETA = 0.10


def find_context(
    context: Sequence[str],
    target_words: Sequence[str],
) -> list[int]:
    '''Find every position where the context appears in target_words

    context が target_words 中に連続して現れる位置をすべて返す。

    Args:
        context: Sequence of words to search for. 探索する語の列。
        target_words: Sequence to search in. 探索対象の列。

    Returns:
        List of starting indices. 出現開始位置のリスト。
    '''
    indices = []
    for left in range(0, len(target_words)):
        right = left + len(context)
        if context == target_words[left:right]:
            indices.append(left)
    return indices


def calc_word_orders(
    hyp: Sequence[str],
    ref: Sequence[str],
) -> list[int]:
    '''Align each hypothesis word to its rank in the reference

    A word that occurs exactly once in both sentences is aligned directly.
    For an ambiguous word, the surrounding context window is widened until
    the match becomes unique, as in the original RIBES algorithm.

    仮説文の各語を参照文における順位に対応付ける。
    両文でちょうど 1 回だけ出現する語は直接対応付け、曖昧な語は
    一意に定まるまで前後の文脈窓を広げる (原論文のアルゴリズムに従う)。

    Args:
        hyp: Hypothesis word sequence. 仮説文の語列。
        ref: Reference word sequence. 参照文の語列。

    Returns:
        List of reference ranks, in hypothesis order.
            仮説文の順に並んだ参照文側の順位のリスト。
    '''
    orders = []
    hyp_len = len(hyp)
    for i, word in enumerate(hyp):
        if word not in ref:
            # Up to 0.2.x this was "pass", which fell through pointlessly.
            # 0.2.x までは "pass" で無意味に処理が続いていた
            continue
        if hyp.count(word) == 1 and ref.count(word) == 1:
            orders.append(ref.index(word))
            continue
        # The word is ambiguous; widen the context window.
        # 曖昧な語なので文脈窓を広げる
        max_window = max(i, hyp_len - i + 1)
        for window in range(1, max_window):
            if i + window < hyp_len:
                # Right context / 右側の文脈
                right = hyp[i:i + window + 1]
                ref_founds = find_context(right, ref)
                if len(ref_founds) == 1 and len(find_context(right, hyp)) == 1:
                    orders.append(ref_founds[0])
                    break
            if window <= i:
                # Left context / 左側の文脈
                left = hyp[i - window:i + 1]
                ref_founds = find_context(left, ref)
                # Up to 0.2.x this compared against 2 instead of 1.
                # 0.2.x までは 1 ではなく 2 と比較していた
                if len(ref_founds) == 1 and len(find_context(left, hyp)) == 1:
                    orders.append(ref_founds[0] + len(left) - 1)
                    break
    return orders


def calc_normalized_kendalls_tau(orders: Sequence[int]) -> float:
    '''Compute the normalized Kendall's tau of a rank sequence

    The value equals ``(tau + 1) / 2``, i.e. the ratio of ascending pairs,
    and therefore ranges over [0, 1].

    順位列の正規化 Kendall's tau を計算する。
    値は ``(tau + 1) / 2``、すなわち昇順ペアの割合に等しく、[0, 1] を取る。

    Args:
        orders: Sequence of reference ranks. 参照文側の順位の列。

    Returns:
        The normalized Kendall's tau. 正規化 Kendall's tau。

    Examples:
        >>> calc_normalized_kendalls_tau([1, 2, 3])
        1.0
        >>> calc_normalized_kendalls_tau([3, 2, 1])
        0.0
    '''
    n = len(orders)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0
    ascending = 0
    for i, j in combinations(orders, 2):
        if i < j:
            ascending += 1
    return ascending / (n * (n - 1) / 2.0)


def calc_kendalls_tau(
    hyp: Sequence[str],
    ref: Sequence[str],
) -> float:
    '''Compute the normalized Kendall's tau between a hypothesis and reference

    Note that the argument order is (hyp, ref), kept for backward
    compatibility, whereas `eval_ribes` takes (ref, hyp) to match
    `lpu.metrics.bleu.eval_bleu`.

    仮説文と参照文の正規化 Kendall's tau を計算する。
    引数の順序は後方互換のため (hyp, ref) である点に注意
    (`eval_ribes` は `lpu.metrics.bleu.eval_bleu` に合わせて (ref, hyp))。

    Args:
        hyp: Hypothesis word sequence. 仮説文の語列。
        ref: Reference word sequence. 参照文の語列。

    Returns:
        The normalized Kendall's tau. 正規化 Kendall's tau。
    '''
    return calc_normalized_kendalls_tau(calc_word_orders(hyp, ref))


def calc_brevity_penalty(
    ref: Sequence[str],
    hyp: Sequence[str],
) -> float:
    '''Compute the brevity penalty for a short hypothesis

    仮説文が短い場合の短さペナルティを計算する。

    Args:
        ref: Reference word sequence. 参照文の語列。
        hyp: Hypothesis word sequence. 仮説文の語列。

    Returns:
        A penalty in (0, 1]. (0, 1] の範囲のペナルティ。
    '''
    if not hyp:
        return 0.0
    return min(1.0, math.exp(1.0 - len(ref) / len(hyp)))


def eval_ribes(
    ref: Sequence[str],
    hyp: Sequence[str],
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    '''Evaluate the RIBES score of a hypothesis against a reference

    仮説文の RIBES スコアを参照文に対して評価する。

    Args:
        ref: Reference word sequence. 参照文の語列。
        hyp: Hypothesis word sequence. 仮説文の語列。
        alpha: Exponent of the unigram precision. ユニグラム精度の指数。
        beta: Exponent of the brevity penalty. 短さペナルティの指数。

    Returns:
        The RIBES score in [0, 1]. [0, 1] の範囲の RIBES スコア。

    Examples:
        >>> eval_ribes(list('abcd'), list('abcd'))
        1.0
    '''
    if not hyp or not ref:
        return 0.0
    orders = calc_word_orders(hyp, ref)
    nkt = calc_normalized_kendalls_tau(orders)
    precision = len(orders) / len(hyp)
    bp = calc_brevity_penalty(ref, hyp)
    return nkt * (precision ** alpha) * (bp ** beta)
