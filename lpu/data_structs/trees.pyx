# distutils: language=c++
# -*- coding: utf-8 -*-

'''tree expression and operations'''

import copy
from collections import Iterable

# third party library
#import numpy as np

cdef class TreeNode:
    cdef readonly list children
    #cdef Forest children
    #cdef object label
    cdef public str label

    #def __cinit__(self, object label):
    def __cinit__(self, str label):
        self.children = []
        #self.children = Forest()
        self.label = label

    cpdef TreeNode append(self, node):
        if isinstance(node, TreeNode):
            self.children.append(node)
        elif isinstance(node, str):
            self.children.append(TreeNode(node))
        else:
            raise TypeError('expected TreeNode or str, given %s' % type(node))
        return self

    cpdef checkValid(self, deep=True):
        cdef TreeNode node
        if len(self.label) == 0 and len(self.children) > 0:
            return False
        if not deep:
            return True
        for node in self.children:
#            if not node.checkValid(True):
                return False
        return True

    @staticmethod
    def fromS(str expr):
        cdef TreeNode t = TreeNode('')
        cdef TreeNode tmp
        return t

    cpdef str toStr(self):
#        cdef str strChildren = ''
#        map(Tree.toStr, self.children)
        cdef str strChildren = ''
        cdef TreeNode node
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

    def __str__(self):
        return self.toStr()
    def __repr__(self):
        cdef str mod = str(self.__class__.__module__)
        try:
            return "%s.fromS(%r)" % (mod,self.toStr())
        except:
            return "%s.fromS(__invalid__)" % (mod,)

Tree = TreeNode

#cdef __findMin(str target, sub, start = 0, end = None):
#    cdef str key
#    cdef int found
#    cdef int minFound = -1
#    if isinstance(sub, str):
#        return target.find(sub, start, end)
#    elif isinstance(sub, Iterable):
#        for key in sub:
#            found = target.find(key, start, end)
#            if minFound < 0:
#                minFound = found
#            else:
#                minFound = min(minFound, found)
#        return minFound

cpdef object parseSExpression(str expr, int i = 0):
    cdef object cont = ''
    cdef object item
    while i < len(expr):
        #dprint('Expr[%s]: %s' % (i, expr[i]))
        if expr[i] == '(':
            #dprint('Push')
            cont = []
            while i < len(expr):
                if expr[i] == ')':
                    #dprint("Closing: %s" % cont)
                    return cont, i + 1
                item, i = parseSExpression(expr, i + 1)
                if item:
                    #print("Appending: %s" % item)
                    cont.append(item)
            return cont, i
        elif expr[i] == ')':
            #dprint("Closing: " + cont)
            return cont, i
        elif expr[i] == ' ':
            #dprint('Elem: ' + cont)
            return cont, i
        else:
            cont += expr[i]
            i += 1
    return cont, i

def indexTree(list tree):
    #cdef list indexToTree = []
    cdef list indexToLabel = []
    cdef list indexToLeftRange = []
    def appendNodePostOrder(object node):
        cdef leftRange = -1
        cdef index
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
    appendNodePostOrder(tree)
    #return indexToTree
    return indexToLabel, indexToLeftRange

def countElements(list tree):
    def innerCount(object node):
        cdef int numElems = 0
        if isinstance(node, list):
            if len(node) > 0:
                for sub in node[1:]:
                    numElems += innerCount(sub)
            return numElems + 1
        else:
            # leaf
            return 1
    return innerCount(tree)

#import pprint
cpdef calcEditDistance(seq1, seq2):
    cdef list memo = [[None]*(len(seq2)+1) for _ in range(0,len(seq1)+1)]
    cdef int i, j
    for i in range(0, len(seq1)+1):
        memo[i][0] = i
    for j in range(0, len(seq2)+1):
        memo[0][j] = j
    for i in range(1, len(seq1)+1):
        for j in range(1, len(seq2)+1):
            #print("--")
            #print("i: %s (%s), j: %s (%s)" % (i, seq1[:i], j, seq2[:j]))
            if seq1[i-1] == seq2[j-1]:
                memo[i][j] = min(memo[i-1][j]+1, memo[i][j-1]+1, memo[i-1][j-1])
            else:
                memo[i][j] = min(memo[i-1][j]+1, memo[i][j-1]+1, memo[i-1][j-1]+1)
            #pprint.pprint(memo)
    #pprint.pprint(memo)
    return memo[len(seq1)][len(seq2)]

import pprint
def calcTreeEditDistance(object tree1, object tree2):
    cdef dict memo = {}
    #cdef object memo
    cdef list indexToLabel1
    cdef list indexToLeftRange1
    cdef list indexToLabel2
    cdef list indexToLeftRange2
    cdef int numNodes1
    cdef int numNodes2
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
    def calcInnerDistance(int left1, int right1, int left2, int right2):
        #print("(%s,%s) vs (%s,%s)" % (left1, right1, left2, right2))
        cdef v1, v2, v3, v
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
        #    return memo[left1, right1, left2, right2]
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
        #print("%s,%s :: %s,%s" % (indexToLabel1[left1:right1+1], indexToLeftRange1[left1:right1+1], indexToLabel2[left2:right2+1], indexToLeftRange2[left2:right2+1]))
        #print("(%s,%s) vs (%s,%s) -> min(%s,%s,%s) = %s" % (left1, right1, left2, right2, v1, v2, v3, v))
        #print("(%s,%s) vs (%s,%s) -> %s" % (left1, right1, left2, right2, v))
        #print("------")
        return v
    #return calcInnerDistance(0, len(indexToLabel1)-1, 0, len(indexToLabel2)-1)
    return calcInnerDistance(0, numNodes1-1, 0, numNodes2-1)


