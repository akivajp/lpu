#cdef class StackHolder:
cdef class StackHolder(object):
    #cdef readonly bool affect_system
    cdef readonly bint affect_system
    cdef readonly int level
    cdef dict env_layer
    cdef list back_log

    cpdef clear(self)
    cpdef set(self, str key, str value)
    cpdef unset(self, str key)
