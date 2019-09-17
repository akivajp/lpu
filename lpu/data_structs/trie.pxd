# C++ types
from libcpp.string cimport string
from libcpp.deque cimport deque

# local library
from lpu.common cimport compat

#ctypedef string& ref_string

cdef class IDMap(object):
    # members
    cdef object dict
    cdef list unusedIDs
    cdef int numEmpty
    # methods
    cpdef long append(self, str key)
    cpdef long remove(self, str key)
    cpdef long str2id(self, str key)

cdef class TwoWayIDMap(IDMap):
    # member
    cdef deque[string] keyList
    # methods
    cpdef long append(self, str key)
    cpdef str id2str(self, long num)
    cpdef void purge(self)
    cpdef long remove(self, str key)

cdef class Dict(object):
    # members
    cdef IDMap idmap
    cdef list objectList
    # methods
    cpdef object get(self, str key, object default=*)
    cpdef object remove(self, str key)
    cpdef object setdefault(self, str key, object value)
    cdef object __set(self, str key, object value)
