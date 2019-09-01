#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
os.environ['DEBUG'] = '1'

from lpu.metrics import bleu
from lpu.common import logging
from lpu.common.logging import debug_print as dprint

if __name__ == '__main__':
    ref = 'abcdef'
    hyp1 = 'bcdf'
    dprint(ref)
    dprint(hyp1)
    dprint(bleu.calc_ngram_precision(ref, hyp1, 1, False), )
    dprint(bleu.calc_ngram_precision(ref, hyp1, 2, False), )
    dprint(bleu.calc_ngram_precision(ref, hyp1, 3, False), )
    dprint(bleu.calc_ngram_precision(ref, hyp1, 4, False), )
    dprint(bleu.calc_ngram_precision(ref, hyp1, 1, True), )
    dprint(bleu.calc_ngram_precision(ref, hyp1, 2, True), )
    dprint(bleu.calc_ngram_precision(ref, hyp1, 3, True), )
    dprint(bleu.calc_ngram_precision(ref, hyp1, 4, True), )
    dprint(bleu.calc_breavity_penalty(ref, hyp1), )
    dprint(bleu.eval_bleu(ref, hyp1, 3, False))
    dprint(bleu.eval_bleu(ref, hyp1, 4, False))
    dprint(bleu.eval_bleu(ref, hyp1, 4, True))

    hyp2 = '^abcdef$'
    dprint(hyp2)
    dprint(bleu.calc_ngram_precision(ref, hyp2, 4, False), )
    dprint(bleu.calc_ngram_precision(ref, hyp2, 4, True), )
    dprint(bleu.calc_breavity_penalty(ref, hyp2), )
    dprint(bleu.eval_bleu(ref, hyp2, 4, False))
    dprint(bleu.eval_bleu(ref, hyp2, 4, True))

