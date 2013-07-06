'''Unit testing helpers.'''

import sys
import token
import tokenize
import unittest
from cStringIO import StringIO
from itertools import izip


CBIND_PACKAGE_LOCATION = '..'

def prepare():
    '''Set up sys.path so that unit tests will import local package
       instead of the installed one.
    '''
    if CBIND_PACKAGE_LOCATION not in sys.path:
        sys.path.insert(0, CBIND_PACKAGE_LOCATION)

prepare()
from cbind import CtypesBindingGenerator

class TestCtypesBindingGenerator(unittest.TestCase):
    '''Boilerplate of unit tests.'''

    def run_test(self, c_code, python_code):
        '''Generate Python code from C code and compare it to the answer.'''
        c_src = StringIO(c_code)
        cbgen = CtypesBindingGenerator()
        cbgen.parse('input.c', contents=c_src)
        output = StringIO()
        cbgen.generate(output)
        self.assert_equivalent(output.getvalue(), python_code)

    def assert_equivalent(self, code1, code2):
        '''Test if Python codes are equivalent.'''
        unimportant_token_types = frozenset(
                (token.NEWLINE, token.INDENT, token.DEDENT, 54))
        def get_tokens(code):
            '''Return tokens important to comparison.'''
            tokens = tokenize.generate_tokens(StringIO(code).readline)
            for token_type, token_str, _, _, _ in tokens:
                if token_type not in unimportant_token_types:
                    yield token_str
        for token1, token2 in izip(get_tokens(code1), get_tokens(code2)):
            self.assertEqual(token1, token2)
