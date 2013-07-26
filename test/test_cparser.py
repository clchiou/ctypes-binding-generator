'''Unit tests of C expression tokenizer.'''

import unittest
from cStringIO import StringIO

from cbind.macro_const import Token, Expression, Parser


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
                Token(Token.END, None),
                )


class TestExpression(unittest.TestCase):

    def compare_expr(self, output, answer):
        self.assertEqual(output.this, answer.this)
        self.assertEqual(output.left is None, answer.left is None)
        self.assertEqual(output.right is None, answer.right is None)
        if output.left:
            self.compare_expr(output.left, answer.left)
        if output.right:
            self.compare_expr(output.right, answer.right)

    def test_syntax(self):
        c_expr = 'x + y * z'
        parser = Parser()
        expr = parser.parse(c_expr)
        self.compare_expr(expr,
                Expression(this=Token(Token.BINOP, '+'),
                    left=Expression(this=Token(Token.SYMBOL, 'x'),
                        left=None, right=None),
                    right=Expression(this=Token(Token.BINOP, '*'),
                        left=Expression(this=Token(Token.SYMBOL, 'y'),
                            left=None, right=None),
                        right=Expression(this=Token(Token.SYMBOL, 'z'),
                            left=None, right=None)
                        )
                    )
                )
        output = StringIO()
        expr.translate(output)
        self.assertEqual(output.getvalue(), c_expr)
