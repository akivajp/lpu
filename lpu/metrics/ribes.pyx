# distutils: language=c++
# -*- coding: utf-8 -*-

'''
    functions to evaluate RIBES scores
'''

from itertools import combinations

def find_context(context, target_words):
    indices = []
    for left in range(0, len(target_words)):
        right = left + len(context)
        if context == target_words[left:right]:
            indices.append(left)
    return indices

def calc_kendalls_tau(hyp, ref):
    orders = []
    for i, word in enumerate(hyp):
        if word not in ref:
            pass
        if hyp.count(word) == 1 and ref.count(word) == 1:
            orders.append(ref.index(word))
        else:
            for length in range(2, len(hyp)):
                context1 = hyp[i:i+length]
                context2 = hyp[i-length+1:i+1]
                hyp_founds1 = find_context(context1, hyp)
                ref_founds1 = find_context(context1, ref)
                hyp_founds2 = find_context(context2, hyp)
                ref_founds2 = find_context(context2, ref)
                if len(hyp_founds1) == 1 and len(ref_founds1) == 1:
                    orders.append(ref_founds1[0])
                    break
                elif len(hyp_founds2) == 1 and len(ref_founds2) == 2:
                    orders.append(ref_founds2[0]+length-1)
                    break
                elif len(ref_founds1) == 0 and len(ref_founds2) == 0:
                    break
    #print(orders)
    n = len(orders)
    if n == 0:
        return 0.0
    elif n == 1:
        return 1.0
    else:
        ascending = 0
        for i, j in combinations(orders, 2):
            if i < j:
                ascending += 1
        return ascending / (n * (n - 1) / 2.0)

