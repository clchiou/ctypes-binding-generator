'''Unit tests of C expression tokenizer.'''

import unittest

from cbind.macro_const import Token


class TestCExprTokenizer(unittest.TestCase):

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
                1ul''',
                Token(Token.SYMBOL,     '__file__'),
                Token(Token.LITERAL,    '"\\"hello world\\""'),
                Token(Token.LITERAL,    '\'\\\'\''),
                Token(Token.LITERAL,    '3.14'),
                Token(Token.BINOP,      '+'),
                Token(Token.BINOP,      '-'),
                Token(Token.BINOP,      '*'),
                Token(Token.BINOP,      '/'),
                Token(Token.LITERAL,    '1ul'))
