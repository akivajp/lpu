# -*- coding: utf-8 -*-

'''
    functions to evaluate BLEU scores
'''

from collections import defaultdict
from collections.abc import Sequence
from functools import reduce
import math

from lpu.common import logging
from lpu.common.logging import debug_print as dprint

def get_ngram_count(words: Sequence[str], n: int) -> defaultdict[tuple[str, ...], int]:
    ngram_count: defaultdict[tuple[str, ...], int] = defaultdict(int)
    for left in range(0, len(words)-n+1):
        #ngram = str.join(' ', words[left:left+n])
        ngram = tuple(words[left:left+n])
        ngram_count[ngram] += 1
    return ngram_count

def calc_ngram_precision(
    ref: Sequence[str],
    hyp: Sequence[str],
    n: int,
    smooth: bool = False,
) -> float:
    ref_ngram_count = get_ngram_count(ref, n)
    hyp_ngram_count = get_ngram_count(hyp, n)
    total = 0
    correct = 0
    for ngram, count in hyp_ngram_count.items():
        total += count
        correct += min(count, ref_ngram_count[ngram])
    if total == 0:
        return 0.0
    if smooth and n >= 2:
        return (correct + 1) / float(total + 1)
    else:
        return correct / float(total)

def calc_breavity_penalty(ref: Sequence[str], hyp: Sequence[str]) -> float:
    if len(hyp) >= len(ref):
        return 1.0
    else:
        return math.exp(1 - len(ref) / float(len(hyp)))

def eval_bleu(
    ref: Sequence[str],
    hyp: Sequence[str],
    order: int = 4,
    smooth: bool = False,
) -> float:
    precisions = []
    for i in range(1, order+1):
        precisions.append( calc_ngram_precision(ref, hyp, i, smooth) )
    bp = calc_breavity_penalty(ref, hyp)
    geometric_mean = math.pow(reduce(float.__mul__, precisions), 1 / float(order))
    return geometric_mean * bp

