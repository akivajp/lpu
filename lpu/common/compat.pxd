# fused type
ctypedef fused strtype:
    str
    bytes
    #unicode

# converting functions
cdef bytes py2_bytes_to_str(bytes b)
cdef str py3_bytes_to_str(bytes b)
cdef unicode py2_bytes_to_unicode(bytes b)
cdef unicode py3_bytes_to_unicode(bytes b)
cdef bytes py2_str_to_bytes(bytes s)
cdef bytes py3_str_to_bytes(str s)
cdef unicode py2_str_to_unicode(bytes s)
cdef unicode py3_str_to_unicode(str s)
cdef bytes py2_unicode_to_bytes(unicode u)
cdef bytes py3_unicode_to_bytes(unicode u)
cdef bytes py2_unicode_to_str(unicode u)
cdef str py3_unicode_to_str(unicode u)

cdef bytes py2_to_bytes(object o)
cdef bytes py3_to_bytes(object o)
cdef bytes py2_to_str(object o)
cdef str py3_to_str(object o)
cdef unicode py2_to_unicode(object o)
cdef unicode py3_to_unicode(object o)

