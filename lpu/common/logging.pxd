from lpu.common cimport environ

#cdef class CustomLogger(logging.Logger):
#    pass

cdef class LoggingStatus(environ.StackHolder):
    #cdef list loggers
    cdef set loggers

cpdef using_config(object loggers, object debug=*, object quiet=*)

cdef _get_cached_line(str path, unsigned int lineno, object fallback=*, object frame=*)

cdef _get_cached_calls(str path, unsigned int lineno, object fallback=*, object frame=*)
cdef _get_call_key(object call)

cdef _seek_args(str path, unsigned int lineno, object fallback=*, object frame=*)
cdef _parse_args(str buf, object feeder, unsigned int offset=*, unsigned int depth=*)
cdef _seek_str(str buf, unsigned int offset)
