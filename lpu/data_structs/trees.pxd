import cython

ctypedef fused node_type:
    TreeNode
    str

cdef class TreeNode(object):
    # members
    cdef readonly list children
    cdef public str label
    # methods
    #cpdef TreeNode append(self, node)
    cpdef TreeNode append(self, node_type node)

    @cython.locals(node = TreeNode)
    cpdef checkValid(self, deep=*)

    #@staticmethod
    #@cython.returns(TreeNode)
    #cpdef TreeNode fromS(expr)

    @cython.locals(strChildren = str)
    @cython.locals(node = TreeNode)
    cpdef str toStr(self)

@cython.locals(cont = object)
@cython.locals(item = object)
cpdef object parseSExpression(str expr, int i=*)

#@cython.locals(indexToLabel = list)
#@cython.locals(indexToLeftRange = list)
#cpdef indexTree(tree)

#cpdef countElements(tree)

@cython.locals(memo = list)
@cython.locals(i = int, j = int)
cpdef calcEditDistance(seq1, seq2)

#@cython.locals(memo = dict)
#@cython.locals(indexToLabel1 = list)
#@cython.locals(indexToLeftRange1 = list)
#@cython.locals(indexToLabel2 = list)
#@cython.locals(indexToLeftRange2 = list)
#@cython.locals(numNodes1 = int)
#@cython.locals(numNodes2 = int)
#cpdef calcTreeEditDistance(object tree1, object tree2)
