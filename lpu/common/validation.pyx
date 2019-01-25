# distutils: language=c++
# -*- coding: utf-8 -*-

'''
    Utility functions for validation
'''

def to_type_names_string(types, conjunction='or'):
    if isinstance(types, (list, tuple)):
        length = len(types)
        if length == 0:
            raise ValueError("Expected non-empty list or tuple, but given empty: {}".format(types))
        elif length == 1:
            return to_type_names_string(types[0])
        else:
            type_names = list(map(to_type_names_string, types))
            if length == 2:
                return '{} {} {}'.format(type_names[0], conjunction, type_names[1])
            else:
                left = str.join(', ', type_names[0:-1])
                right = type_names[-1]
                return '{} {} {}'.format(left, conjunction, right)
    else:
        elem = types
        if isinstance(elem, type):
            return elem.__name__
        else:
            raise TypeError("Expected type object, but given non-type object: {}".format(elem))

def check_argument_type(val, name, expected_types):
    if isinstance(expected_types, list):
        expected_types = tuple(expected_types)
    if isinstance(val, expected_types):
        # OK
        return True
    else:
        type_names = to_type_names_string(expected_types)
        tmp_error = 'Invalid type of argument `{}` is given: expected {}, but given {}'
        raise TypeError(tmp_error.format(name, type_names, type(val).__name__))

