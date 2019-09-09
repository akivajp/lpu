from lpu.common cimport compat

# constants
cdef str BACK_WHITE
cdef long DEFAULT_BUFFER_SIZE
#cdef double DEFAULT_REFRESH_INTERVAL
cdef float DEFAULT_REFRESH_INTERVAL

# classes
cdef class SpeedCounter(object):
    #cdef readonly bool force
    cdef readonly bint force
    #cdef readonly str header
    cdef readonly object header
    #cdef readonly double refresh
    cdef readonly float refresh
    cdef readonly double start_time, last_time # should be double, otherwise rounding errors cause problems
    cdef readonly long count, pos, last_count, max_count
    cdef readonly str color

    cpdef add(self, unsigned long count=*, bint view=*)

    cpdef flush(self)

    cpdef reset(self, object refresh=*, object header=*, object force=*, object color=*)

    cpdef set_count(self, unsigned long count, bint view=*)

    cpdef set_position(self, unsigned long position, bint view=*)

    cpdef view(self, bint flush=*)


cdef class FileReader(object):
    cdef SpeedCounter counter
    cdef object source

    cpdef close(self)

    cpdef bytes read(self, size)

    cdef bytes _read_byte_line(self, bint countup=*)
    cpdef bytes read_byte_line(self)

    cpdef str readline(self)

    cpdef long tell(self) except *


cdef class Iterator(object):
    cdef SpeedCounter counter
    cdef object source

    cdef close(self)


# functions
cdef str format_time(unsigned long seconds)

cdef str about(num, bint show_bytes=*)

cpdef FileReader open(object path, str header=*)

cpdef object pipe_view(object filepaths, object mode=*, str header=*, float refresh=*, object outfunc=*)

cpdef object view(object source, object header=*, long max_count=*, bint env=*)
