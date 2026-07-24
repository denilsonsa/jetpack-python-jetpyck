#!/usr/bin/env python3

import doctest
import sys

# Hack to make it possible to test it without installing it.
sys.path.insert(0, "./src")


def run_tests():
    # If you know a better way to test, feel free to enlighten me.

    summary = []
    total_modules = 0
    total_failure = 0
    total_tests = 0

    from jetpyck import gfxdat, level, rle, utils

    for module in [gfxdat, level, rle, utils]:
        failure_count, test_count = doctest.testmod(
            module, optionflags=doctest.IGNORE_EXCEPTION_DETAIL
        )
        summary.append(
            "{}: {} failures out of {} tests".format(
                module.__name__, failure_count, test_count
            )
        )
        total_modules += 1
        total_failure += failure_count
        total_tests += test_count
    summary.append(
        "Total: {} failures out of {} tests from {} modules".format(
            total_failure, total_tests, total_modules
        )
    )
    print("\n".join(summary))
    if total_failure > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
