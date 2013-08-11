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
foo = 0
bar = 1
        ''')

    def test_named_enum(self):
        self.run_test('''
enum my_enum {
    foo,
    bar,
};
        ''', '''
class my_enum(c_uint):
    pass
foo = 0
bar = 1
        ''')


if __name__ == '__main__':
    unittest.main()
