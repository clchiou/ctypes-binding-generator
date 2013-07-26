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
        self.parser = Parser()

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
                msg = 'Could not parse marco: #define %s %s'
                logging.info(msg, symbol, value)

        candidates = enumerate_candidates(c_path)
        for symbol, arguments, body in parse_c_source(c_path, args):
            if symbol not in candidates:
                pass
            elif arguments is not None:
                self._parse_macro_function(symbol, arguments, body)
            else:
                translate_const(symbol, body)
        if int_expr:
            gen = translate_integer_expr(c_path, args, int_expr)
            for symbol, value in gen:
                self.symbol_table[symbol] = None, value

    def _parse_macro_function(self, symbol, arguments, body):
        '''Parse macro function.'''
        if not body:
            return
        try:
            py_expr = self.parser.parse(body)
        except CSyntaxError:
            msg = 'Could not parse macro: #define %s(%s) %s'
            logging.info(msg, symbol, ', '.join(arguments), body)
        else:
            self.symbol_table[symbol] = arguments, py_expr

    def generate(self, output):
        '''Generate macro constants.'''
        for symbol, (arguments, body) in self.symbol_table.iteritems():
            assert body, 'empty value: %s' % repr(body)
            if arguments is not None:
                output.write('%s = lambda %s: \n' %
                        (symbol, ', '.join(arguments)))
                body.translate(output)
                output.write('\n')
            else:
                output.write('%s = %s\n' % (symbol, body))


# A parser of a subset of C syntax is implemented for translating macro
# functions.  This should be good enough for the common cases.


class CSyntaxError(Exception):
    '''Raised when C syntax error.'''
    pass


class Parser:
    '''A parser of a subset of C expression syntax.'''

    # pylint: disable=R0903

    def __init__(self):
        '''Initialize the object.'''
        self._tokens = None
        self._prev_token = None

    def parse(self, c_expr):
        '''Parse C expression.'''
        self._tokens = Token.get_tokens(c_expr)
        self._prev_token = None
        return self._expr()

    def _next(self):
        '''Return next token.'''
        if not self._prev_token:
            try:
                token = self._tokens.next()
            except StopIteration:
                raise CSyntaxError('End of token sequence')
            return token
        token = self._prev_token
        self._prev_token = None
        return token

    def _putback(self, token):
        '''Put back this token.'''
        if self._prev_token is not None:
            raise CSyntaxError('Previous is not empty: %s' % self._prev_token)
        self._prev_token = token

    def _match(self, *matches, **kwargs):
        '''Match this token.'''
        error = kwargs.get('error', True)
        token = self._next()
        for match in matches:
            kind, spellings = match[0], match[1:]
            if token.kind is not kind:
                continue
            if spellings and token.spelling not in spellings:
                continue
            if token.kind is Token.END:
                self._putback(token)
            return token
        if error:
            raise CSyntaxError('Could not match %s' % token)
        self._putback(token)
        return None

    def _expr(self):
        '''Parse expr.'''
        left = self._term()
        this = self._match((Token.BINOP, '+', '-'), (Token.END,), error=False)
        if not this or this.kind is Token.END:
            return left
        right = self._expr()
        return Expression(this=this, left=left, right=right)

    def _term(self):
        '''Parse term.'''
        left = self._factor()
        this = self._match((Token.BINOP, '*', '/'), (Token.END,), error=False)
        if not this or this.kind is Token.END:
            return left
        right = self._term()
        return Expression(this=this, left=left, right=right)

    def _factor(self):
        '''Parse factor.'''
        this = self._match((Token.SYMBOL,),
                (Token.INT_LITERAL,), (Token.FP_LITERAL,),
                (Token.PARENTHESES, '('))
        if this.kind is not Token.PARENTHESES:
            return Expression(this=this, left=None, right=None)
        expr = self._expr()
        self._match((Token.PARENTHESES, ')'))
        expr.parentheses = True  # pylint: disable=W0201
        return expr


class Expression(namedtuple('Expression', 'this left right')):
    '''C expression.'''

    # pylint: disable=W0232,E1101,R0903

    def translate(self, output):
        '''Translate C expression to Python codes.'''
        parentheses = hasattr(self, 'parentheses') and self.parentheses
        if parentheses:
            output.write('(')
        if self.left:
            self.left.translate(output)
            output.write(' ')
        self.this.translate(output)
        if self.right:
            output.write(' ')
            self.right.translate(output)
        if parentheses:
            output.write(')')


class Token(namedtuple('Token', 'kind spelling')):
    '''C token.'''

    # pylint: disable=W0232,E1101

    regex_token = re.compile(r'''
            (?P<symbol>[a-zA-Z_]\w*) |
            (?P<string_literal>\w?"(?:[^"]|\")*") |
            (?P<char_literal>\w?'(?:[^']|\')+') |
            # Floating-point literal must be listed before integer literal...
            (?P<floating_point_literal>
                \d*\.\d+(?:[eE][+\-]?\d+)?[fFlL]? |
                \d+\.\d*(?:[eE][+\-]?\d+)?[fFlL]?
            ) |
            (?P<integer_literal>
                0[xX][a-fA-F0-9]+[uUlL]* |
                0\d+[uUlL]* |
                \d+[uUlL]* |
                \d+[eE][+\-]?\d+[fFlL]?
            ) |
            (?P<binary_operator>
                (?:>>|<<|[+\-*/%&\^|<>=!])=? | && | \|\| | ->
            ) |
            (?P<parentheses>
                [()\[\]{}]
            ) |
            # Ignore the following kinds of tokens for now...
            \+\+ | -- |
            [;,:~?] | <% | %> | <: | :> |
            \.\.\. |
            \s+
            ''', re.VERBOSE)

    SYMBOL          = 'SYMBOL'
    BINOP           = 'BINOP'
    CHAR_LITERAL    = 'CHAR_LITERAL'
    STR_LITERAL     = 'STR_LITERAL'
    INT_LITERAL     = 'INT_LITERAL'
    FP_LITERAL      = 'FP_LITERAL'
    PARENTHESES     = 'PARENTHESES'
    END             = 'END'

    @classmethod
    def get_tokens(cls, c_expr):
        '''Make token list from C expression.'''
        pos = 0
        while True:
            match = cls.regex_token.match(c_expr, pos)
            if not match:
                break
            pos = match.end()
            for gname, kind in (
                    ('symbol',                  cls.SYMBOL),
                    ('char_literal',            cls.CHAR_LITERAL),
                    ('string_literal',          cls.STR_LITERAL),
                    ('integer_literal',         cls.INT_LITERAL),
                    ('floating_point_literal',  cls.FP_LITERAL),
                    ('binary_operator',         cls.BINOP),
                    ('parentheses',             cls.PARENTHESES),
                    ):
                spelling = match.group(gname)
                if spelling:
                    yield cls(kind=kind, spelling=spelling)
                    break
        yield cls(kind=cls.END, spelling=None)

    def translate(self, output):
        '''Translate this token to Python codes.'''
        if self.kind is self.CHAR_LITERAL:
            output.write('ord(%s)' % self.spelling)
        elif self.kind is self.BINOP and self.spelling == '&&':
            output.write('and')
        elif self.kind is self.BINOP and self.spelling == '||':
            output.write('or')
        elif self.kind is self.INT_LITERAL or self.kind is self.FP_LITERAL:
            output.write(self.spelling.rstrip('fFuUlL'))
        else:
            output.write(self.spelling)


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
