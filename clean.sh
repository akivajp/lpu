#!/bin/bash

rm -rfv build
rm -rfv dist
find . -name '*.c' -or -name '*.cpp' -or -name '*.pyc' -or -name '*.so' -or -name '*.egg-info' | xargs rm -rv

