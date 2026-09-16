#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Utility functions handling colors'''

# C++ setting


import logging

logger = logging.getLogger(__name__)

COLOR_MAP = {
    'clear' : '\033[0m',
    'black' : '\033[30m',
    'red'   : '\033[31m',
    'green' : '\033[32m',
    'yellow': '\033[33m',
    'blue'  : '\033[34m',
    'purple': '\033[35m',
    'cyan'  : '\033[36m',
    'white' : '\033[37m'
}

def put_color(content, color=None, eachline=True):
    code = COLOR_MAP.get(color, None)
    #code = colors[color]
    if code:
        if eachline:
            #lines = str(content).split('\n')
            lines = ("%s" % (content,)).split('\n')
            #lines = ['{}{}{}'.format(code, line.rstrip(), COLOR_MAP['clear']) for line in lines]
            lines = ['%s%s%s' % (code, line.rstrip(), COLOR_MAP['clear']) for line in lines]
            return str.join('\n', lines)
        else:
            #return "%s%s%s" % (code, content, COLOR_MAP['clear'])
            #return '{}{}{}'.format(code, content, COLOR_MAP['clear'])
            return '%s%s%s' % (code, content, COLOR_MAP['clear'])
    else:
        return content
