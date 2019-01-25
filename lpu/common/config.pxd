cdef class ConfigData:
    cdef object __base
    cdef dict __dict__

cdef class Config:
    cdef readonly ConfigData data

