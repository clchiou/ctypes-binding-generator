import unittest
import helper


class TestFunction(helper.TestCtypesBindingGenerator):

    def test_simple_function(self):
        self.run_test('''
int foo(int);
        ''', '''
foo = _lib.foo
foo.argtypes = [c_int]
foo.restype = c_int
        ''')


if __name__ == '__main__':
    unittest.main()
