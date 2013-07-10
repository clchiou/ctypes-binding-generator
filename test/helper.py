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

        output = StringIO()
        output.write('Codes are not equivalent:\n')
        self._format_two_column(python_code, gen_code, output)
        output.write('\n')
        self._format_ast(cbgen.translation_units, output)
        error_message = output.getvalue()

        self.assert_equivalent(gen_code, python_code, error_message)
        compile(gen_code, 'output.py', 'exec')

    def assert_equivalent(self, code1, code2, error_message):
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
            self.assertEqual(token1, token2, error_message)

    @staticmethod
    def _format_two_column(code1, code2, output):
        '''Format codes in two column.'''
        input1 = StringIO(code1)
        input2 = StringIO(code2)
        while True:
            line1 = input1.readline()
            line2 = input2.readline()
            if not line1 and not line2:
                break
            line1 = line1.rstrip()
            line2 = line2.rstrip()
            output.write('{0:<38} | {1:<38}\n'.format(line1, line2))

    @staticmethod
    def _format_ast(tunits, output):
        '''Format translation units.'''
        def traverse(cursor, indent):
            '''Traverse and print astree.'''
            if cursor.location.file:
                begin = ('%s%s:%s' % (indent,
                    cursor.location.file.name, cursor.location.line))
            else:
                begin = '%s?:%s' % (indent, cursor.location.line)
            if cursor.spelling:
                name = cursor.spelling
            else:
                name = '\'\''
            output.write('{0:<24} {1:<24} {2}\n'.format(begin,
                name, cursor.kind))
            for child in cursor.get_children():
                traverse(child, indent + '  ')

        for tunit in tunits:
            traverse(tunit.cursor, '')
