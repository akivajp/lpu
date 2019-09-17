#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  test the module: lpu.data_structs.trees
"""

import os
os.environ["LPU_DEBUG"] = "1"

from lpu.common import logging
from lpu.data_structs import trees

logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

def test_seqs(seq1, seq2):
    logger.debug("-" * 40)
    dprint(seq1)
    dprint(seq2)
    dprint(trees.calcEditDistance(seq1, seq1))
    dprint(trees.calcEditDistance(seq1, seq2))

def test_trees(tree1, tree2):
    logger.debug("-" * 40)
    dprint(tree1)
    dprint(tree2)
    dprint(trees.calcTreeEditDistance(tree1, tree1))
    dprint(trees.calcTreeEditDistance(tree1, tree2))

if __name__ == '__main__':
    dprint(trees)
    dprint(dir(trees))
    test_seqs("A", "B")
    test_seqs("AAA", "BAB")
    test_seqs("ABRA", "CADABRA")
    tree1 = trees.Tree("root1")
    tree2 = trees.Tree("root2")
    test_trees(tree1, tree2)
    tree1.append("A")
    test_trees(tree1, tree2)
    tree2.append("A")
    test_trees(tree1, tree2)
    tree1.append("B")
    test_trees(tree1, tree2)
    tree2.append("C")
    test_trees(tree1, tree2)
    test_trees("(A A)", "(A B C)")
