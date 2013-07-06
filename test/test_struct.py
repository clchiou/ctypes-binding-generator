import unittest
import helper


class TestStruct(helper.TestCtypesBindingGenerator):

    def test_simple_struct(self):
        self.run_test('''
struct foo {
    int bar;
};
        ''', '''
class foo(Structure):
    _pack_ = 4
    _fields_ = [('bar', c_int)]
        ''')

    def test_nested_struct(self):
        self.run_test('''
struct bar {
    struct foo {
        int i
    } s;
};
        ''', '''
class foo(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

class bar(Structure):
    _pack_ = 4
    _fields_ = [('s', foo)]
        ''')


if __name__ == '__main__':
    unittest.main()
