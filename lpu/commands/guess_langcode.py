#!/usr/bin/env python

import argparse
import sys

def guessLangCodeFromFileName(filepath):
    fields = filepath.split('.')
    fields.reverse()
    for field in fields:
        if len(field) == 2:
            return field.lower()
    return "UNK"

def printLangCodeList(filepaths):
    print(str.join(' ', map(guessLangCodeFromFileName, filepaths)))

def cmdGuessLangCode(args):
    parser = argparse.ArgumentParser(description='Guess the language codes from given files')
    parser.add_argument('filepaths', metavar="filepath", nargs="+", type=str, help='path of file to guess the language code')
    #parser.add_argument('--from-filename', '-n', action='store_true', help='guess from the file name (default)')
    parsed = parser.parse_args(args)
    printLangCodeList(parsed.filepaths)

def main():
    cmdGuessLangCode(sys.argv[1:])

if __name__ == '__main__':
    main()

