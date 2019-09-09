cdef class ConfigData(object):
    cdef readonly ConfigData __base
    cdef readonly object __main

cdef class Config(object):
    cdef readonly ConfigData base
    cdef readonly ConfigData data

    cpdef load_json(self, str str_json, bint override=*)
    cpdef to_dict(self, str key=*, bint ordered=*, bint upstream=*, bint recursive=*, bint purge=*, bint flat=*)

#cpdef get_items(object data, bint purge)

cdef bint should_take(object val, bint purge)

cdef object data2dict(object data, object dtype, bint upstream, bint recursive, bint purge)

cdef object dict2data(object obj)

cdef str get_key_val_str(object d, bint verbose)

cdef list flat_items(object items, str prefix, bint chain_key)
cdef object flat_dict(object d, type dtype, bint chain_key)

cdef ConfigData _update_data(ConfigData cdata, object _conf=*, bint _override=*, bint _override_none=*)
