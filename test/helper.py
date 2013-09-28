'''Unit testing helpers.'''

import os
import tempfile
import token
import tokenize
import unittest
from cbind.compatibility import StringIO
from cbind.config import SyntaxTreeMatcher
from cbind.ctypes_binding import CtypesBindingGenerator
from cbind.macro import MacroGenerator
from cbind.mangler import mangle


class TestCtypesBindingGenerator(unittest.TestCase):
    '''Boilerplate of unit tests.'''

    # pylint: disable=R0913
    def run_test(self, c_code, python_code,
            filename='input.c', args=None, config=None):
        '''Generate Python code from C code and compare it to the answer.'''
        cbgen = CtypesBindingGenerator()
        if config is not None:
            import yaml
            config = yaml.load(config)
            cbgen.config(config)
        if isinstance(c_code, str):
            c_src = StringIO(c_code)
            cbgen.parse(filename, contents=c_src, args=args)
        else:
            for filename, code in c_code:
                c_src = StringIO(code)
                cbgen.parse(filename, contents=c_src, args=args)
        output = StringIO()
        if config and 'preamble' in config:
            cbgen.generate_preamble('cbind', None, output)
        cbgen.generate(output)
        gen_code = output.getvalue()

        error_message = prepare_error_message(python_code, gen_code,
                tunits=cbgen.get_translation_units())
        self.assertTrue(compare_codes(gen_code, python_code), error_message)
        compile(gen_code, 'output.py', 'exec')


class TestCppMangler(unittest.TestCase):
    '''Boilerplate of unit tests.'''

    def _make_symbol_table(self, symbols, root):
        '''Make symbol table.'''
        symbol_table = []
        for spec, mangled_name in symbols:
            if isinstance(spec, str):
                symbol = spec
                matcher = SyntaxTreeMatcher.make([{'name': '^%s$' % spec}])
            else:
                symbol = spec['name']
                matcher = SyntaxTreeMatcher.make([spec])
            symbol_table.append({
                'symbol': symbol,
                'matcher': matcher,
                'mangled_name': mangled_name,
            })
        def search_node(tree):
            '''Search matched node.'''
            for blob in symbol_table:
                if blob['matcher'].do_match(tree):
                    self.assertTrue('tree' not in blob)  # Unique matching
                    blob['tree'] = tree
        root.traverse(preorder=search_node)
        for blob in symbol_table:
            blob['output_name'] = mangle(blob['tree'])
        return symbol_table

    def run_test(self, cpp_code, symbols, args=None):
        '''Test mangler.'''
        cbgen = CtypesBindingGenerator()
        cpp_src = StringIO(cpp_code)
        cbgen.parse('input.cpp', contents=cpp_src, args=args)
        root = cbgen.syntax_tree_forest[0]
        symbol_table = self._make_symbol_table(symbols, root)
        errmsg = StringIO()
        errmsg.write('In comparing mangled names:\n')
        for blob in symbol_table:
            symbol = blob['symbol']
            mangled_name = blob['mangled_name']
            output_name = blob['output_name']
            if mangled_name != output_name:
                errmsg.write('Mangling symbol %s: %s != %s\n' %
                        (repr(symbol), repr(mangled_name), repr(output_name)))
        format_ast([root.translation_unit], errmsg)
        errmsg = errmsg.getvalue()
        for blob in symbol_table:
            mangled_name = blob['mangled_name']
            output_name = blob['output_name']
            self.assertEqual(mangled_name, output_name, errmsg)


class TestMacroGenerator(unittest.TestCase):
    '''Boilerplate of unit tests.'''

    def setUp(self):
        self.header_fd, self.header_path = tempfile.mkstemp(suffix='.h')

    def tearDown(self):
        os.remove(self.header_path)

    def run_test(self, c_code, python_code, macro_int=None, stderr=None):
        '''Generate Python code from C code and compare it to the answer.'''
        with os.fdopen(self.header_fd, 'w') as header_file:
            header_file.write(c_code)

        mcgen = MacroGenerator(macro_int=macro_int)
        mcgen.parse(self.header_path, None, stderr=stderr)
        output = StringIO()
        mcgen.generate(output)
        gen_code = output.getvalue()

        error_message = prepare_error_message(python_code, gen_code)
        self.assertTrue(compare_codes(gen_code, python_code), error_message)


def compare_codes(code1, code2):
    '''Test if Python codes are equivalent.'''
    unimportant_token_types = frozenset(
            (token.NEWLINE, token.INDENT, token.DEDENT, token.N_TOKENS + 1))
    def get_tokens(code):
        '''Return tokens important to comparison.'''
        tokens = tokenize.generate_tokens(StringIO(code).readline)
        for token_type, token_str, _, _, _ in tokens:
            if token_type not in unimportant_token_types:
                yield token_str
    for token1, token2 in zip(get_tokens(code1), get_tokens(code2)):
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
        output.write('{0!s:<24} {1!s:<24} {2!s}\n'.format(begin,
            name, cursor.kind))
        for child in cursor.get_children():
            traverse(child, indent + '  ')

    for tunit in tunits:
        traverse(tunit.cursor, '')
