#from libcpp cimport bool

#cdef class StringEnumerator:
cdef class StringEnumerator(object):
    cdef dict dict_str2id
    cdef list list_id2str

    #cpdef bool append(self, str string)
    cpdef bint append(self, str string)
    cpdef long str2id(self, str string)
    cpdef str id2str(self, long number)

cdef StringEnumerator word_enum
cdef StringEnumerator phrase_enum

cpdef long word2id(str word)
cpdef str id2word(long number)
cpdef str phrase2idvec(str phrase)
cpdef str idvec2phrase(str idvec)
cpdef long phrase2id(str phrase)
cpdef str id2phrase(long number)
