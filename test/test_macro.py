import unittest
import helper


class TestMacro(helper.TestMacroConstantGenerator):

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


if __name__ == '__main__':
    unittest.main()
