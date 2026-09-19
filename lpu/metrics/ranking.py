#!/usr/bin/env python

'''
    functions to evaluate ranking metrics

    ランキング指標 (Precision@k, MRR) を算出する関数群。

    Each function takes the ranks of the correct items, where a rank is
    1-based (the top of the ranking is rank 1). `None` denotes an item that
    the ranking did not retrieve at all; it is counted as a miss rather than
    raising, so that a ranker returning `None` for out-of-candidate items can
    be evaluated directly.

    いずれの関数も正解アイテムの順位列を受け取る。順位は 1 始まり
    (ランキング最上位が 1) で、`None` は「ランキングに現れなかった」ことを
    表し、例外ではなく不正解として数える (候補外のアイテムに `None` を返す
    ランカーの出力をそのまま評価できるようにするため)。
'''

from collections.abc import Sequence


def calc_precision_at_k(ranks: Sequence[int | None], k: int) -> float:
    '''Calculate Precision@k from the ranks of the correct items

    正解アイテムの順位列から Precision@k を算出する。

    Args:
        ranks: 1-based ranks of the correct items; `None` means not retrieved.
            正解アイテムの 1 始まりの順位。`None` は未検出を表す。
        k: The cut-off rank (must be 1 or greater).
            打ち切り順位 (1 以上)。

    Returns:
        The ratio of the queries whose correct item ranked within the top k.
            正解が上位 k 件に入ったクエリの割合。

    Raises:
        ValueError: If `ranks` is empty, `k` is less than 1, or a rank is
            not a positive integer.
            `ranks` が空、`k` が 1 未満、順位が正の整数でない場合。

    Examples:
        >>> calc_precision_at_k([1, 2, 5], 2)
        0.6666666666666666
        >>> calc_precision_at_k([1, None], 10)
        0.5
    '''
    if k < 1:
        raise ValueError(f"k must be 1 or greater, given: {k}")
    # 空の順位列では割合が定義できないため、0 除算ではなく明示的に弾く
    if not ranks:
        raise ValueError("ranks must not be empty")
    matched = 0
    for rank in ranks:
        if rank is None:
            # 未検出は常に不正解として数える
            continue
        _validate_rank(rank)
        if rank <= k:
            matched += 1
    return matched / len(ranks)


def calc_mean_reciprocal_rank(ranks: Sequence[int | None]) -> float:
    '''Calculate the Mean Reciprocal Rank (MRR) from the ranks of the correct items

    正解アイテムの順位列から MRR (平均逆順位) を算出する。

    Args:
        ranks: 1-based ranks of the correct items; `None` means not retrieved
            and contributes a reciprocal rank of 0.
            正解アイテムの 1 始まりの順位。`None` は未検出を表し、
            逆順位 0 として寄与する。

    Returns:
        The mean of the reciprocal ranks.
            逆順位の平均値。

    Raises:
        ValueError: If `ranks` is empty or a rank is not a positive integer.
            `ranks` が空、または順位が正の整数でない場合。

    Examples:
        >>> calc_mean_reciprocal_rank([1, 2, 4])
        0.5833333333333334
        >>> calc_mean_reciprocal_rank([1, None])
        0.5
    '''
    if not ranks:
        raise ValueError("ranks must not be empty")
    total = 0.0
    for rank in ranks:
        if rank is None:
            # 未検出の逆順位は 0 (加算しない)
            continue
        _validate_rank(rank)
        total += 1.0 / rank
    return total / len(ranks)


def _validate_rank(rank: int) -> None:
    '''Reject a rank that is not a positive integer

    正の整数でない順位を弾く。

    A rank of 0 or less would silently distort Precision@k and blow up the
    reciprocal in MRR, so it is rejected at the point it enters.

    0 以下の順位は Precision@k を静かに歪め、MRR では逆数が発散するため、
    受け取った時点で弾く。
    '''
    if rank < 1:
        raise ValueError(f"rank must be 1 or greater (1-based), given: {rank}")
