#!/usr/bin/env python

'''
    Utility functions for validation
'''

def to_type_names_string(
    types: type | list[type] | tuple[type, ...],
    conjunction: str = 'or',
) -> str:
    '''Render type(s) as a human readable string

    型 (またはその列) を人間可読な文字列に整形する。

    Examples:
        >>> to_type_names_string(int)
        'int'
        >>> to_type_names_string([str, bytes])
        'str or bytes'
        >>> to_type_names_string((int, float, str))
        'int, float or str'
    '''
    if isinstance(types, (list, tuple)):
        length = len(types)
        if length == 0:
            raise ValueError(f"Expected non-empty list or tuple, but given empty: {types}")
        elif length == 1:
            return to_type_names_string(types[0])
        else:
            type_names = list(map(to_type_names_string, types))
            if length == 2:
                return f'{type_names[0]} {conjunction} {type_names[1]}'
            else:
                left = str.join(', ', type_names[0:-1])
                right = type_names[-1]
                return f'{left} {conjunction} {right}'
    else:
        elem = types
        if isinstance(elem, type):
            return elem.__name__
        else:
            raise TypeError(f"Expected type object, but given non-type object: {elem}")

def check_argument_type(
    val: object,
    name: str,
    expected_types: type | list[type] | tuple[type, ...],
) -> bool:
    if isinstance(expected_types, list):
        expected_types = tuple(expected_types)
    if isinstance(val, expected_types):
        # OK
        return True
    else:
        type_names = to_type_names_string(expected_types)
        tmp_error = 'Invalid type of argument `{}` is given: expected {}, but given {}'
        raise TypeError(tmp_error.format(name, type_names, type(val).__name__))

