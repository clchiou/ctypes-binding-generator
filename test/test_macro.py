import unittest
import helper


class TestMacro(helper.TestMacroGenerator):

    def test_simple_macro(self):
        self.run_test('''
#define A
#define B 1
#define C 0x10
#define D 007
#define E 3.14
#define F "hello world"
        ''', '''
B = 1
C = 0x10
D = 007
E = 3.14
F = "hello world"
        ''')

    def disable_test_macro_int(self):
        self.run_test('''
#define A (1 + 1)
#define B A * 3
#define C A * 4
        ''', '''
A = 2
B = 6
        ''',
        regex_integer_typed='[AB]')

    def test_macro_str(self):
        self.run_test('''
#define A "hello" " world"
#define B 'a'
#define C 'a' + 3
#define D __func__
#define E "this is " __func__
        ''', '''
B = ord('a')
C = ord('a') + 3
D = __func__
        ''',
        regex_integer_typed='C')

    def test_macro_function(self):
        self.run_test('''
#define A() 0
#define B(x) x
#define C(x, y) x * y
#define D(x, y, z) x + y - z
#define E()
#define F(x)
        ''', '''
A = lambda : 0
B = lambda x: x
C = lambda x, y: x * y
D = lambda x, y, z: x + y - z
        ''')


if __name__ == '__main__':
    unittest.main()
