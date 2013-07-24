'''Generate Python codes from macro constants.'''

import logging
import os
import re
import subprocess
import tempfile
from collections import OrderedDict, namedtuple
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
        int_expr = []
        def translate_const(symbol, value):
            '''Translate macro value to Python codes.'''
            py_value = simple_translate_value(value)
            if py_value is not None:
                self.symbol_table[symbol] = None, py_value
            elif regex_integer_typed and regex_integer_typed.match(symbol):
                # We could not parse the value, but since user assures us that
                # this value is integer-typed, we will give it another try...
                int_expr.append((symbol, value))
                self.symbol_table[symbol] = None, None
            else:
                msg = 'Could not translate macro constant: %s = %s'
                logging.info(msg, symbol, value)

        def translate_macro_body(symbol, arguments, body):
            '''Translate macro body into Python codes.'''
            if not body:
                return
            # TODO(clchiou): libclang does not export much of the ASTree.
            # It looks like we cannot implement a C-to-Python translator
            # from libclang.  What should we do?
            self.symbol_table[symbol] = arguments, body

        candidates = enumerate_candidates(c_path)
        for symbol, arguments, body in parse_c_source(c_path, args):
            if symbol not in candidates:
                pass
            elif arguments is not None:
                translate_macro_body(symbol, arguments, body)
            else:
                translate_const(symbol, body)
        if int_expr:
            gen = translate_integer_expr(c_path, args, int_expr)
            for symbol, value in gen:
                self.symbol_table[symbol] = None, value

    def generate(self, output):
        '''Generate macro constants.'''
        for symbol, (arguments, body) in self.symbol_table.iteritems():
            assert body, 'empty value: %s' % repr(body)
            if arguments is not None:
                output.write('%s = lambda %s: %s\n' %
                        (symbol, ', '.join(arguments), body))
            else:
                output.write('%s = %s\n' % (symbol, body))


class Token(namedtuple('Token', 'kind spelling')):
    '''C Token.'''

    # pylint: disable=W0232,R0903

    regex_token = re.compile(r'''
            [a-zA-Z_]\w* |
            \w?"(?:[^"]|\")*" |
            \w?'(?:[^']|\')+' |

            # Floating-point literal must be before integer literal...
            \d*\.\d+(?:[eE][+\-]?\d+)?[fFlL]? |
            \d+\.\d*(?:[eE][+\-]?\d+)?[fFlL]? |

            0[xX][a-fA-F0-9]+[uUlL]* |
            0\d+[uUlL]* |
            \d+[uUlL]* |
            \d+[eE][+\-]?\d+[fFlL]? |

            [();,:\[\]~?{}] | <% | %> | <: | :> |
            \.\.\. |
            (?:>>|<<|[+\-*/%&\^|<>=!])=? | && | \|\| |
            \+\+ | -- | ->
            ''', re.VERBOSE)

    regex_symbol = re.compile(r'[a-zA-Z_]\w*')

    regex_binop = re.compile(r'''
            (?:
                >> |
                << |
                [+\-*/%&\^|<>=!]
            )=? |
            && |
            \|\| |
            \. |
            ->
            ''', re.VERBOSE)

    SYMBOL  = 'SYMBOL'
    BINOP   = 'BINOP'
    LITERAL = 'LITERAL'

    @classmethod
    def get_tokens(cls, c_expr):
        '''Make token list from C expression.'''
        for token in cls.regex_token.findall(c_expr):
            if cls.regex_symbol.match(token):
                yield cls(cls.SYMBOL, token)
            elif cls.regex_binop.match(token):
                yield cls(cls.BINOP, token)
            elif '"' in token or "'" in token:
                yield cls(cls.LITERAL, token)
            elif any(c.isdigit() for c in token):
                yield cls(cls.LITERAL, token)
            else:
                pass


REGEX_DEFINE = re.compile(r'\s*#\s*define\s+(\w+)')
REGEX_ARGUMENTS = re.compile(r'''
        \(
            \s*
            (
                \w+
                (?:
                    \s*,\s*\w+
                )*
            )?
            \s*
        \)''', re.VERBOSE)


def enumerate_candidates(c_path):
    '''Get locally-defined macro names.'''
    candidates = set()
    with open(c_path) as c_src:
        for c_src_line in c_src:
            match = REGEX_DEFINE.match(c_src_line)
            if match:
                candidates.add(match.group(1))
    return candidates


def parse_c_source(c_path, args):
    '''Run gcc preprocessor and get values of the symbols.'''
    symbol_arg_body = []
    gcc = ['gcc', '-E', '-dM', c_path]
    gcc.extend(args or ())
    macros = StringIO(subprocess.check_output(gcc))
    for define_line in macros:
        match = REGEX_DEFINE.match(define_line)
        if not match:
            continue
        symbol = match.group(1)
        value = define_line[match.end():]
        arguments, body = match_macro_function(value)
        symbol_arg_body.append((symbol, arguments, body))
    return symbol_arg_body


def match_macro_function(value):
    '''Match macro function arguments'''
    match = REGEX_ARGUMENTS.match(value)
    if not match:
        return None, value.strip()
    arguments = match.group(1)
    if arguments:
        arguments = tuple(arg.strip() for arg in arguments.split(','))
    else:
        arguments = ()
    body = value[match.end():].strip()
    return arguments, body


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

    regex_name = re.compile('^%s_(\w+)$' % magic)
    for cursor in nodes:
        for enum in cursor.get_children():
            match = regex_name.match(enum.spelling)
            if match:
                yield (match.group(1), str(enum.enum_value))
