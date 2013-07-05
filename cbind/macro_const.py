'''Generate Python codes from macro constants.'''

import logging
import os
import re
import subprocess
import tempfile
from collections import OrderedDict
from itertools import chain
from clang.cindex import Index, CursorKind


class MacroConstantsException(Exception):
    '''Exception raised by MacroConstantsGenerator class.'''
    pass


class MacroConstantsGenerator:
    '''Generate Python code from macro constants.'''

    magic = '__macro_symbol_magic'

    def __init__(self):
        '''Initialize object.'''
        self.local_symbols = []
        self.c_sources = []
        self.symbol_table = OrderedDict()

    def preprocess(self, c_source):
        '''Search the source file for locally-defined macros constants.'''
        with open(c_source) as src:
            regex_def = re.compile(r'\s*#\s*define\s+([\w_]+)')
            for src_line in src:
                match = regex_def.match(src_line)
                if not match:
                    continue
                # TODO(clchiou): Parse macro function; ignore it for now.
                if src_line[match.end()] == '(':
                    continue
                self.local_symbols.append(match.group(1))
        self.c_sources.append(c_source)

    def parse(self, args=None, included_symbols=None, excluded_symbols=None,
            regex_integer_typed=None):
        '''Parse the source files.'''
        symbol_values = self._get_symbol_values(args or (),
                included_symbols or (), excluded_symbols or ())
        assured_integer_symbols = self._translate_symbol_values(symbol_values,
                regex_integer_typed)
        if assured_integer_symbols:
            self._translate_integer_symbols(assured_integer_symbols, args)

    def _get_symbol_values(self, args, included_symbols, excluded_symbols):
        '''Get value of the symbols.'''
        tmp_src_fd, tmp_src_path = tempfile.mkstemp(suffix='.c')
        try:
            with os.fdopen(tmp_src_fd, 'w') as tmp_src:
                for c_src_path in self.c_sources:
                    c_src_path = os.path.abspath(c_src_path)
                    tmp_src.write('#include "%s"\n' % c_src_path)
                for symbol in chain(included_symbols, self.local_symbols):
                    if symbol in excluded_symbols:
                        continue
                    tmp_src.write('{0}_{1} = {1}\n'.format(self.magic, symbol))
            clang = ['clang', '-E', tmp_src_path]
            clang.extend(args)
            preprocessed = subprocess.check_output(clang)
        finally:
            os.remove(tmp_src_path)
        regex = re.compile('^%s_([\w_]+) = (.*)$' % self.magic, re.MULTILINE)
        return regex.findall(preprocessed)

    def _translate_symbol_values(self, symbol_values, regex_integer_typed):
        '''Translate symbol values into Python codes.'''
        assured_integer_symbols = []
        for symbol, value in symbol_values:
            value = value.strip()
            # Now comes the dirty part: We guess the type of value, and
            # translate the value into Python codes accordingly.
            for guess in (self._guess_str, self._guess_int, self._guess_float):
                translated_value = guess(value)
                if translated_value is not None:
                    self.symbol_table[symbol] = translated_value
                    break
            else:
                # We could not parse the value, but since user assures us that
                # this value is integer-typed, we will give it another try...
                if regex_integer_typed and regex_integer_typed.match(symbol):
                    assured_integer_symbols.append((symbol, value))
                    self.symbol_table[symbol] = None
                else:
                    msg = 'Could not translate macro constant: %s = %s'
                    logging.info(msg, symbol, value)
        return assured_integer_symbols

    @staticmethod
    def _guess_str(value):
        '''Guess value is string valued.'''
        for sep in '\'"':
            if value.startswith(sep) and value.endswith(sep):
                return value
        return None

    @staticmethod
    def _guess_int(value):
        '''Guess value is int valued.'''
        try:
            int(value, 0)
        except ValueError:
            return None
        else:
            return value

    @staticmethod
    def _guess_float(value):
        '''Guess value is float valued.'''
        try:
            float(value)
        except ValueError:
            return None
        else:
            return value

    def _translate_integer_symbols(self, integer_symbols, args):
        '''Translate integer-typed symbols.'''
        tunit = self._run_clang(integer_symbols, args)
        cursors = []
        self._find(tunit.cursor, self._is_enum_def, cursors)
        if not cursors:
            msg = 'Could not find enum in generated C source'
            raise MacroConstantsException(msg)
        regex_name = re.compile('^%s_([\w_]+)$' % self.magic)
        for cursor in cursors:
            for enum in cursor.get_children():
                match = regex_name.match(enum.spelling)
                if not match:
                    continue
                self.symbol_table[match.group(1)] = str(enum.enum_value)

    def _run_clang(self, integer_symbols, args):
        '''Run clang on integer symbols.'''
        tmp_src_fd, tmp_src_path = tempfile.mkstemp(suffix='.c')
        try:
            with os.fdopen(tmp_src_fd, 'w') as tmp_src:
                for c_src_path in self.c_sources:
                    c_src_path = os.path.abspath(c_src_path)
                    tmp_src.write('#include "%s"\n' % c_src_path)
                tmp_src.write('enum {\n')
                for symbol, value in integer_symbols:
                    tmp_src.write('%s_%s = %s,\n' %
                            (self.magic, symbol, value))
                tmp_src.write('};\n')
            index = Index.create()
            tunit = index.parse(tmp_src_path, args=args)
            if not tunit:
                msg = 'Could not parse generated C source'
                raise MacroConstantsException(msg)
        finally:
            os.remove(tmp_src_path)
        return tunit

    def _find(self, cursor, predicate, result):
        '''Recursively walk through the AST to find the cursors.'''
        for child in cursor.get_children():
            self._find(child, predicate, result)
        if predicate(cursor):
            result.append(cursor)

    @staticmethod
    def _is_enum_def(cursor):
        '''Test if the cursor is an enum definition.'''
        return cursor.kind is CursorKind.ENUM_DECL and cursor.is_definition()

    def generate(self, output):
        '''Generate macro constants.'''
        for symbol, value in self.symbol_table.iteritems():
            assert value, 'empty value: %s' % repr(value)
            output.write('%s = %s\n' % (symbol, value))
