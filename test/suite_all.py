import sys
import unittest

import test_builtin
import test_config
import test_cparser
import test_enum
import test_function
import test_include
import test_macro
import test_multiple_sources
import test_struct
import test_typedef
import test_union
import test_variable


suite_all = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromModule(test_builtin),
    unittest.TestLoader().loadTestsFromModule(test_config),
    unittest.TestLoader().loadTestsFromModule(test_cparser),
    unittest.TestLoader().loadTestsFromModule(test_enum),
    unittest.TestLoader().loadTestsFromModule(test_function),
    unittest.TestLoader().loadTestsFromModule(test_include),
    unittest.TestLoader().loadTestsFromModule(test_macro),
    unittest.TestLoader().loadTestsFromModule(test_multiple_sources),
    unittest.TestLoader().loadTestsFromModule(test_struct),
    unittest.TestLoader().loadTestsFromModule(test_typedef),
    unittest.TestLoader().loadTestsFromModule(test_union),
    unittest.TestLoader().loadTestsFromModule(test_variable),
])


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    sys.exit(not runner.run(suite_all).wasSuccessful())
