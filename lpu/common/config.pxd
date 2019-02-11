cdef class ConfigData:
    cdef object __base
    #cdef dict __dict__
    #cdef OrderedDict __dict__
    cdef object __main

cdef class Config:
    cdef readonly ConfigData data

