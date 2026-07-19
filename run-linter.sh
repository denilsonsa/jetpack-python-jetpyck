#!/bin/sh

# Little convenience script that I use while working on the code from this repository.

black src/
mypy --strict --python-executable=`which python3` src/

# Why --python-executable?
# To solve the following error on my machine:
# error: Cannot find implementation or library stub for module named "PIL" [import-not-found]
# https://mypy.readthedocs.io/en/stable/running_mypy.html#cannot-find-implementation-or-library-stub
