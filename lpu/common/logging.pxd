from lpu.common cimport environ

#class class LoggingStatus(environ.StackHolder, object):
cdef class LoggingStatus(environ.StackHolder):
    #cdef list loggers
    cdef set loggers

cpdef using_config(object loggers, object debug=*, object quiet=*)

cpdef _debug_print(self, object val=*, int limit=*)
