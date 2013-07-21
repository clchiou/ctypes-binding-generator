'''Generate Python codes from macro constants.'''

import logging
import os
import re
import subprocess
import tempfile
from collections import OrderedDict
from cStringIO import StringIO
from clang.cindex import Index, CursorKind
from cbind.util import walk_astree


class MacroConstantsException(Exception):
    '''Exception raised by MacroConstantsGenerator class.'''
    pass


class MacroConstantsGenerator:
    '''Generate Python code from macro constants.'''

    def __init__(self):
        '''Initialize object.'''
        self.symbol_table = OrderedDict()

    def parse(self, c_path, args=None, regex_integer_typed=None):
        '''Parse the source files.'''
        symbol_values = parse_symbol_values(c_path, args)
        assured_integer_symbols = []
        candidates = enumerate_candidates(c_path)
        for symbol, value in symbol_values:
            if symbol not in candidates:
                continue
            py_value = simple_translate_value(value)
            if py_value is not None:
                self.symbol_table[symbol] = py_value
            elif regex_integer_typed and regex_integer_typed.match(symbol):
                # We could not parse the value, but since user assures us that
                # this value is integer-typed, we will give it another try...
                assured_integer_symbols.append((symbol, value))
                self.symbol_table[symbol] = None
            else:
                msg = 'Could not translate macro constant: %s = %s'
                logging.info(msg, symbol, value)
        if assured_integer_symbols:
            gen = translate_integer_expr(c_path, args, assured_integer_symbols)
            for symbol, value in gen:
                self.symbol_table[symbol] = value

    def generate(self, output):
        '''Generate macro constants.'''
        for symbol, value in self.symbol_table.iteritems():
            assert value, 'empty value: %s' % repr(value)
            output.write('%s = %s\n' % (symbol, value))


REGEX_DEFINE = re.compile(r'\s*#\s*define\s+([\w_]+)')


def enumerate_candidates(c_path):
    '''Get locally-defined macro names.'''
    candidates = set()
    with open(c_path) as c_src:
        for c_src_line in c_src:
            match = REGEX_DEFINE.match(c_src_line)
            if match:
                candidates.add(match.group(1))
    return candidates


def parse_symbol_values(c_path, args):
    '''Run gcc preprocessor and get values of the symbols.'''
    symbol_values = []
    gcc = ['gcc', '-E', '-dM', c_path]
    gcc.extend(args or ())
    macros = StringIO(subprocess.check_output(gcc))
    for define_line in macros:
        match = REGEX_DEFINE.match(define_line)
        if not match:
            continue
        symbol = match.group(1)
        value = define_line[match.end():]
        if not value[0].isspace():
            # TODO(clchiou): Ignore macro function for now.
            continue
        symbol_values.append((symbol, value.strip()))
    return symbol_values


def simple_translate_value(value):
    '''Translate symbol value into Python codes.'''
    # Guess value is string valued...
    py_value = None
    try:
        py_value = eval(value, {})
    except (SyntaxError, NameError, TypeError):
        pass
    if isinstance(py_value, str):
        if len(py_value) == 1 and value[0] == value[-1] == '\'':
            return 'ord(\'%s\')' % py_value
        return repr(py_value)
    # Guess value is int valued...
    try:
        int(value, 0)
    except ValueError:
        pass
    else:
        return value
    # Guess value is float valued...
    try:
        float(value)
    except ValueError:
        pass
    else:
        return value
    # Okay, it's none of above...
    return None


def translate_integer_expr(c_path, args, symbol_values,
        magic='__macro_symbol_magic'):
    '''Translate integer-typed expression with libclang.'''

    def run_clang(c_path, args, symbol_values, magic):
        '''Run clang on integer symbols.'''
        tmp_src_fd, tmp_src_path = tempfile.mkstemp(suffix='.c')
        try:
            with os.fdopen(tmp_src_fd, 'w') as tmp_src:
                c_abs_path = os.path.abspath(c_path)
                tmp_src.write('#include "%s"\n' % c_abs_path)
                tmp_src.write('enum {\n')
                for symbol, value in symbol_values:
                    tmp_src.write('%s_%s = %s,\n' % (magic, symbol, value))
                tmp_src.write('};\n')
            index = Index.create()
            tunit = index.parse(tmp_src_path, args=args)
            if not tunit:
                msg = 'Could not parse generated C source'
                raise MacroConstantsException(msg)
        finally:
            os.remove(tmp_src_path)
        return tunit
    tunit = run_clang(c_path, args, symbol_values, magic)

    nodes = []
    def search_enum_def(cursor):
        '''Test if the cursor is an enum definition.'''
        if cursor.kind is CursorKind.ENUM_DECL and cursor.is_definition():
            nodes.append(cursor)
    walk_astree(tunit.cursor, search_enum_def)
    if not nodes:
        msg = 'Could not find enum in generated C source'
        raise MacroConstantsException(msg)

    regex_name = re.compile('^%s_([\w_]+)$' % magic)
    for cursor in nodes:
        for enum in cursor.get_children():
            match = regex_name.match(enum.spelling)
            if match:
                yield (match.group(1), str(enum.enum_value))
