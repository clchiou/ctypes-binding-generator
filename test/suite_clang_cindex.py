import sys
import unittest

import cbind
cbind.choose_cindex_impl(cbind.CLANG_CINDEX)

import suite_all


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    sys.exit(not runner.run(suite_all.suite_all).wasSuccessful())
