import unittest
import helper


class TestTypedef(helper.TestCtypesBindingGenerator):

    def test_simple_typedef(self):
        self.run_test('''
typedef int my_type;
        ''', '''
my_type = c_int
        ''')


if __name__ == '__main__':
    unittest.main()
