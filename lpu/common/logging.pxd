from lpu.common cimport environ
from lpu.backends import safe_logging

#cdef class CustomLogger(logging.Logger):
#    pass

cdef class LoggingStatus(environ.StackHolder):
    #cdef list loggers
    cdef set loggers

cpdef using_config(object loggers, object debug=*, object quiet=*)

#cpdef _debug_print(self, object val=*, int limit=*)
