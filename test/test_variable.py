import unittest
import helper


class TestVariable(helper.TestCtypesBindingGenerator):

    def test_simple_variable(self):
        self.run_test('''
extern int foo;
        ''', '''
foo = c_int.in_dll(_lib, 'foo')
        ''')


if __name__ == '__main__':
    unittest.main()
