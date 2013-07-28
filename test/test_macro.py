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
#define G 0x1f
        ''', '''
B = 1
C = 0x10
D = 007
E = 3.14
F = "hello world"
G = 0x1f
        ''')

    def test_macro_dictionary_order(self):
        self.run_test('''
#define B 1
#define A (B + 1)
        ''', '''
B = 1
A = (B + 1)
        ''')

    def test_macro_int(self):
        self.run_test('''
struct foo {
    int i;
};

#define A (1 + 1)
#define B A * 3
#define C sizeof(int*)
#define D sizeof(struct foo)
        ''', '''
A = (1 + 1)
B = A * 3
C = 8
D = 4
        ''',
        macro_int='C|D')

    def test_macro_str(self):
        self.run_test('''
#define A "hello"    " world"
#define B 'a'
#define C 'a' + 3
#define D __func__
#define E "this is " __func__
        ''', '''
A = "hello" " world"
B = ord('a')
C = ord('a') + 3
        ''')

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
