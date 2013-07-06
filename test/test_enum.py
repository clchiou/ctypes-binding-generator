import unittest
import helper


class TestEnum(helper.TestCtypesBindingGenerator):

    def test_simple_enum(self):
        self.run_test('''
enum {
    foo,
    bar,
};
        ''', '''
foo = c_uint(0)
bar = c_uint(1)
        ''')


if __name__ == '__main__':
    unittest.main()
