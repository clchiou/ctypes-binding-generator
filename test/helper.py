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
        gen_code = output.getvalue()
        self.assert_equivalent(gen_code, python_code)
        compile(gen_code, 'output.py', 'exec')

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
        msg = 'Codes are not equivalent:\n'
        two_column = self._format_two_column(msg, code1, code2)
        for token1, token2 in izip(get_tokens(code1), get_tokens(code2)):
            self.assertEqual(token1, token2, two_column)

    @staticmethod
    def _format_two_column(msg, code1, code2):
        '''Format codes in two column.'''
        input1 = StringIO(code1)
        input2 = StringIO(code2)
        output = StringIO()
        output.write(msg)
        while True:
            line1 = input1.readline()
            line2 = input2.readline()
            if not line1 and not line2:
                break
            line1 = line1.rstrip()
            line2 = line2.rstrip()
            output.write('{0:<60} | {1:<60}\n'.format(line1, line2))
        return output.getvalue()
