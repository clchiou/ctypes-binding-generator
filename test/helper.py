'''Unit testing helpers.'''

import os
import tempfile
import token
import tokenize
import unittest
from cStringIO import StringIO
from itertools import izip

from cbind import CtypesBindingGenerator, MacroGenerator


class TestCtypesBindingGenerator(unittest.TestCase):
    '''Boilerplate of unit tests.'''

    def run_test(self, c_code, python_code, args=None):
        '''Generate Python code from C code and compare it to the answer.'''
        c_src = StringIO(c_code)
        cbgen = CtypesBindingGenerator()
        cbgen.parse('input.c', contents=c_src, args=args)
        output = StringIO()
        cbgen.generate(output)
        gen_code = output.getvalue()

        error_message = prepare_error_message(python_code, gen_code,
                tunits=cbgen.get_translation_units())
        self.assertTrue(compare_codes(gen_code, python_code), error_message)
        compile(gen_code, 'output.py', 'exec')


class TestMacroGenerator(unittest.TestCase):
    '''Boilerplate of unit tests.'''

    def setUp(self):
        self.header_fd, self.header_path = tempfile.mkstemp(suffix='.h')

    def tearDown(self):
        os.remove(self.header_path)

    def run_test(self, c_code, python_code, args=None, macro_int=None):
        '''Generate Python code from C code and compare it to the answer.'''
        with os.fdopen(self.header_fd, 'w') as header_file:
            header_file.write(c_code)

        mcgen = MacroGenerator(macro_int=macro_int)
        mcgen.parse(self.header_path, args)
        output = StringIO()
        mcgen.generate(output)
        gen_code = output.getvalue()

        error_message = prepare_error_message(python_code, gen_code)
        self.assertTrue(compare_codes(gen_code, python_code), error_message)


def compare_codes(code1, code2):
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
        if token1 != token2:
            return False
    return True


def prepare_error_message(python_code, gen_code, tunits=None):
    '''Generate standard error message.'''
    output = StringIO()
    output.write('Codes are not equivalent:\n')
    format_two_column(python_code, gen_code, output)
    if tunits:
        output.write('\n')
        format_ast(tunits, output)
    return output.getvalue()


def format_two_column(code1, code2, output):
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


def format_ast(tunits, output):
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
