#!/bin/bash

rm -rf build
rm -rf dist
rm -rf .git
rm -rf *.egg-info
find . -name '*.c' -or -name '*.cpp' | xargs -n 1 rm

