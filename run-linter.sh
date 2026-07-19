#!/bin/sh

black src/
mypy --strict --python-executable=`which python3` src/
