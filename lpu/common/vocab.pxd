from libcpp cimport bool

cdef class StringEnumerator:
    cdef dict dict_str2id
    cdef list list_id2str

    cpdef bool append(self, str string)
    cpdef long str2id(self, str string)
    cpdef str id2str(self, long number)

