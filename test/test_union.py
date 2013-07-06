import unittest
import helper


class TestStruct(helper.TestCtypesBindingGenerator):

    def test_simple_union(self):
        self.run_test('''
union foo {
    int i;
    char c;
};
        ''', '''
class foo(Union):
    _pack_ = 4
    _fields_ = [('i', c_int),
                ('c', c_char)]
        ''')


if __name__ == '__main__':
    unittest.main()
