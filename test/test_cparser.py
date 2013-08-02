'''Unit tests of C expression tokenizer.'''

import unittest
from cStringIO import StringIO

from cbind.macro import Token, Expression, Parser


class TestToken(unittest.TestCase):

    def run_test(self, c_expr, *answer_tokens):
        output_tokens = tuple(Token.get_tokens(c_expr))
        msg = ('%d != %d:\n%s\n%s\n' %
                (len(output_tokens), len(answer_tokens),
                    output_tokens, answer_tokens))
        self.assertEqual(len(output_tokens), len(answer_tokens), msg)
        for output, answer in zip(output_tokens, answer_tokens):
            msg = '%s != %s' % (output, answer)
            self.assertEqual(output, answer, msg)

    def test_tokenizer(self):
        self.run_test('''
                __file__
                "\\"hello world\\""
                '\\''
                3.14
                + - * /
                1ul
                0x1f
                () [] {}
                ,
                ||
                &&
                ->
                ''',
                Token(Token.SYMBOL, '__file__'),
                Token(Token.STR_LITERAL, '"\\"hello world\\""'),
                Token(Token.CHAR_LITERAL, '\'\\\'\''),
                Token(Token.FP_LITERAL, '3.14'),
                Token(Token.BINOP, '+'),
                Token(Token.BINOP, '-'),
                Token(Token.BINOP, '*'),
                Token(Token.BINOP, '/'),
                Token(Token.INT_LITERAL, '1ul'),
                Token(Token.INT_LITERAL, '0x1f'),
                Token(Token.PARENTHESES, '('), Token(Token.PARENTHESES, ')'),
                Token(Token.PARENTHESES, '['), Token(Token.PARENTHESES, ']'),
                Token(Token.PARENTHESES, '{'), Token(Token.PARENTHESES, '}'),
                Token(Token.MISC, ','),
                Token(Token.BINOP, '||'),
                Token(Token.BINOP, '&&'),
                Token(Token.BINOP, '->'),
                Token(Token.END, None),
                )

    def run_token_translate(self, kind, spelling, answer):
        output = StringIO()
        Token(kind, spelling).translate(output)
        self.assertEqual(output.getvalue(), answer)

    def test_token_translate(self):
        self.run_token_translate(Token.BINOP, '&&', 'and')
        self.run_token_translate(Token.BINOP, '||', 'or')
        self.run_token_translate(Token.CHAR_LITERAL, '\'x\'', 'ord(\'x\')')
        self.run_token_translate(Token.INT_LITERAL, '016ul', '016')
        self.run_token_translate(Token.FP_LITERAL, '3.14f', '3.14')


class TestExpression(unittest.TestCase):

    def compare_expr(self, output, answer):
        if isinstance(answer, str):
            self.assertEqual(output.this.spelling, answer)
        else:
            self.assertEqual(output.this.spelling, answer[0])
        if isinstance(answer, str) or len(answer) == 1:
            self.assertFalse(output.children)
            return
        self.assertEqual(len(output.children), len(answer) - 1)
        for child, sub_tree in zip(output.children, answer[1:]):
            self.compare_expr(child, sub_tree)

    def run_test(self, c_expr, answer, py_expr=None):
        parser = Parser()
        expr = parser.parse(c_expr)
        self.compare_expr(expr, answer)
        output = StringIO()
        expr.translate(output)
        self.assertEqual(output.getvalue(), py_expr or c_expr)

    def test_simple_expr(self):
        self.run_test('xx + yy * zz - (1 - 3.14) / a',
                ('+',
                    'xx',
                    ('-',
                        ('*', 'yy', 'zz'),
                        ('/',
                            ('()', ('-', '1', '3.14')),
                            'a'
                            )
                        )
                    )
                )
        self.run_test('xx || yy && zz;',
                ('||', 'xx', ('&&', 'yy', 'zz')),
                'xx or yy and zz')
        self.run_test('x ? y : z',
                ('?:', 'x', 'y', 'z'),
                'y if x else z')
        self.run_test('- +x',
                ('-', ('+', 'x')),
                '-+x')
        self.run_test('!!1',
                ('!', ('!', '1')),
                'not not 1')

    def test_function_call(self):
        self.run_test('f(1, 2, 3)', ('()', 'f', '1', '2', '3'))
        self.run_test('f(x)', ('()', 'f', 'x'))
        self.run_test('f()', ('()', 'f'))


if __name__ == '__main__':
    unittest.main()
