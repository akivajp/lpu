#!/usr/bin/env python

'''tree expression and operations'''

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from lpu.common import logging
logger = logging.getColorLogger(__name__)
dprint = logger.debug_print

class TreeNode:

    #def __cinit__(self, object label):
    #def __cinit__(self, str label):
    def __init__(self, label: str):
        self.children: list[TreeNode] = []
        #self.children = Forest()
        self.label = label

    def append(self, node: TreeNode | str) -> TreeNode:
        if isinstance(node, TreeNode):
            self.children.append(node)
        elif isinstance(node, str):
            self.children.append(TreeNode(node))
        #    raise TypeError('expected TreeNode or str, given %s' % type(node))
        return self

    def checkValid(self, deep: bool = True) -> bool:
        '''check whether this node (and optionally its subtree) is valid

        A node is invalid when it has children but an empty label.
        Note: up to 0.2.x the recursive check was commented out while its
        "return False" was left behind, so a deep check reported any node
        with children as invalid.

        このノード (deep=True なら部分木全体) が妥当かを判定する。
        子を持つのにラベルが空のノードは不正とみなす。
        注意: 0.2.x までは再帰判定がコメントアウトされたまま
        "return False" だけが残っており、子を持つノードは deep 判定で
        常に不正と報告されていた。
        '''
        if len(self.label) == 0 and len(self.children) > 0:
            return False
        if not deep:
            return True
        for node in self.children:
            if not node.checkValid(True):
                return False
        return True

    @staticmethod
    def fromS(expr: str) -> TreeNode:
        '''build a tree from an S-expression string

        Note: up to 0.2.x this ignored its argument and always returned an
        empty node.

        S 式の文字列から木を構築する。
        注意: 0.2.x までは引数を無視して常に空ノードを返していた。

        Args:
            expr: S-expression, e.g. "(S (NP the cat) (VP sat))".
                S 式。例: "(S (NP the cat) (VP sat))"

        Returns:
            The root TreeNode. 根の TreeNode。

        Examples:
            >>> tree = TreeNode.fromS('(S (NP the cat) (VP sat))')
            >>> tree.label
            'S'
            >>> [child.label for child in tree.children]
            ['NP', 'VP']
            >>> str(tree)
            '(S (NP (the) (cat)) (VP (sat)))'
        '''
        parsed, _ = parseSExpression(expr)
        return TreeNode._fromParsed(parsed)

    @staticmethod
    def _fromParsed(parsed: str | list) -> TreeNode:
        '''convert the nested lists of parseSExpression into TreeNodes

        parseSExpression が返す入れ子リストを TreeNode に変換する。
        '''
        if not isinstance(parsed, list):
            return TreeNode(parsed)
        if not parsed:
            return TreeNode('')
        # The head is the label and the rest are the children
        # 先頭がラベル、残りが子ノード
        node = TreeNode(parsed[0])
        for sub in parsed[1:]:
            node.append(TreeNode._fromParsed(sub))
        return node

    def toStr(self) -> str:
#        map(Tree.toStr, self.children)
        strChildren = ''
        if not self.checkValid(False):
            raise ValueError( (self.label, self.children) )
        if self.children:
            for node in self.children:
                if strChildren:
                    strChildren += ' '
                strChildren += node.toStr()
            return '(' + self.label + ' ' + strChildren + ')'
        else:
            return '(' + self.label + ')'

    def __str__(self) -> str:
        return self.toStr()
    def __repr__(self) -> str:
        mod = str(self.__class__.__module__)
        try:
            return f"{mod}.fromS({self.toStr()!r})"
        except Exception:
            return f"{mod}.fromS(__invalid__)"

Tree = TreeNode

#    if isinstance(sub, str):
#        return target.find(sub, start, end)
#    elif isinstance(sub, Iterable):
#        for key in sub:
#            found = target.find(key, start, end)
#            if minFound < 0:
#                minFound = found
#                minFound = min(minFound, found)
#        return minFound

def parseSExpression(expr: str, i: int = 0) -> tuple[str | list, int]:
    # `cont` holds a str while scanning a token and a list inside parens;
    # the two shapes are mutually exclusive per path, so it is typed as Any.
    # cont はトークン走査中は str、'(' 内では list になり、経路ごとに
    # 排他であるため Any として型付けする。
    cont: Any = ''
    while i < len(expr):
        if expr[i] == '(':
            cont = []
            while i < len(expr):
                if expr[i] == ')':
                    return cont, i + 1
                item, i = parseSExpression(expr, i + 1)
                if item:
                    cont.append(item)
            return cont, i
        elif expr[i] == ')':
            return cont, i
        elif expr[i] == ' ':
            return cont, i
        else:
            cont += expr[i]
            i += 1
    return cont, i

#def indexTree(list tree):
def indexTree(tree: str | list) -> tuple[list, list[int]]:
    indexToLabel = []
    indexToLeftRange = []
    #def appendNodePostOrder(object node):
    def appendNodePostOrder(node: str | list) -> int:
        #global appendNodePostOrder
        #global indexToLabel
        #global indexToLeftRange
        leftRange = -1
        if isinstance(node, list):
            if len(node) > 0:
                # top/inner node
                for sub in node[1:]:
                    # child node
                    #appendNodePostOrder(sub)
                    index = appendNodePostOrder(sub)
                    if leftRange < 0 or index < leftRange:
                        leftRange = index
                #indexToTree.append(node)
                indexToLabel.append(node[0])
                indexToLeftRange.append(leftRange)
                return leftRange
        else:
            # leaf
            leftRange = len(indexToLabel)
            indexToLabel.append(node)
            indexToLeftRange.append(leftRange)
            #return len(indexToLabel) - 1
            return leftRange
        # an empty list node has no children to inspect; report -1 instead
        # of the implicit None, which would crash the comparison at the caller
        # (空リストノードには子が無いため、暗黙の None の代わりに -1 を返す。
        #  None では呼び出し側の比較でクラッシュする)
        return leftRange
    appendNodePostOrder(tree)
    #return indexToTree
    return indexToLabel, indexToLeftRange

#def countElements(list tree):
def countElements(tree: str | list) -> int:
    #def innerCount(object node):
    def innerCount(node: str | list) -> int:
        numElems = 0
        if isinstance(node, list):
            if len(node) > 0:
                for sub in node[1:]:
                    numElems += innerCount(sub)
            return numElems + 1
        else:
            # leaf
            return 1
    return innerCount(tree)

def calcEditDistance(seq1: Sequence[str], seq2: Sequence[str]) -> int:
    # Every cell below is written before it is ever read (row 0 and column 0
    # explicitly, the rest in the loop), so the initial value is irrelevant.
    # 全てのセルは参照前に必ず書き込まれる (0 行目・0 列目は初期化ループ、
    # 残りは本ループ) ため、初期値自体には意味が無い。
    memo: list[list[int]] = [[0]*(len(seq2)+1) for _ in range(0,len(seq1)+1)]
    for i in range(0, len(seq1)+1):
        memo[i][0] = i
    for j in range(0, len(seq2)+1):
        memo[0][j] = j
    for i in range(1, len(seq1)+1):
        for j in range(1, len(seq2)+1):
            if seq1[i-1] == seq2[j-1]:
                memo[i][j] = min(memo[i-1][j]+1, memo[i][j-1]+1, memo[i-1][j-1])
            else:
                memo[i][j] = min(memo[i-1][j]+1, memo[i][j-1]+1, memo[i-1][j-1]+1)
            #pprint.pprint(memo)
    #pprint.pprint(memo)
    return memo[len(seq1)][len(seq2)]

def calcTreeEditDistance(tree1: str | list, tree2: str | list) -> int:
    memo: dict[tuple[int, int, int, int], int] = {}
    if isinstance(tree1, str) and tree1.strip()[0] == '(':
        # S-expression
        tree1 = parseSExpression(tree1)[0]
    if isinstance(tree2, str) and tree2.strip()[0] == '(':
        # S-expression
        tree2 = parseSExpression(tree2)[0]
    indexToLabel1, indexToLeftRange1 = indexTree(tree1)
    indexToLabel2, indexToLeftRange2 = indexTree(tree2)
    numNodes1 = len(indexToLabel1)
    numNodes2 = len(indexToLabel2)
    #memo = - np.ones([numNodes1,numNodes1,numNodes2,numNodes2])
    ## Forest2 Right
    #memo = [None] * for len(indexToLabel2)
    ## Forest2 Left
    #memo = [copy.deepcopy(memo) for _ in indexToLabel2]
    ## Forest1 Right
    #memo = [copy.deepcopy(memo) for _ in indexToLabel1]
    ## Forest1 Left
    #memo = [copy.deepcopy(memo) for _ in indexToLabel1]
    #def calcInnerDistance(int left1, int right1, int left2, int right2):

    def calcInnerDistance(left1: int, right1: int, left2: int, right2: int) -> int:
        #pprint.pprint((left1, right1, left2, right2))
        #pprint.pprint(memo)
        if left1 < 0 or left2 < 0:
            return 0
        if right1 < left1:
            # empty
            return max(0, right2 - left2 + 1)
        if right2 < left2:
            # empty
            return max(0, right1 - left1 + 1)
        #if left1 < 0 or left1 > right1:
        #    return right2 - left2 + 1
        #if left2 < 0 or left2 > right2:
        #    return right1 - left1 + 1
        #if memo[left1, right1, left2, right2] >= 0:
        if (left1, right1, left2, right2) in memo:
            return memo[left1, right1, left2, right2]
        # v1: modify
        if indexToLabel1[right1] == indexToLabel2[right2]:
            # right top nodes are same
            v1 = 0
        else:
            v1 = 1
        # distance of right most forest
        v1 += calcInnerDistance(
                indexToLeftRange1[right1], right1-1,
                indexToLeftRange2[right2], right2-1,
              )
        # distance of left neighbor forest
        v1 += calcInnerDistance(
                left1, indexToLeftRange1[right1]-1,
                left2, indexToLeftRange2[right2]-1,
              )
        # v2: remove
        v2 = calcInnerDistance(
                left1, right1,
                left2, right2-1
              ) + 1
        # v3: add
        v3 = calcInnerDistance(
                left1, right1-1,
                left2, right2
              ) + 1
        # v: minimal distance
        v = min(v1, v2, v3)
        memo[left1, right1, left2, right2] = v
        #pprint.pprint(memo)
        return v
    #return calcInnerDistance(0, len(indexToLabel1)-1, 0, len(indexToLabel2)-1)
    return calcInnerDistance(0, numNodes1-1, 0, numNodes2-1)
