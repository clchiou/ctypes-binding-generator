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
    pass
foo._fields_ = [('i', c_int),
                ('c', c_char)]
        ''')

        self.run_test('''
union foo {
    int i;
    char c;
};
        ''', '''
class foo(Union):
    pass
foo._fields_ = [('i', c_int),
                ('c', c_char)]
        ''', assert_layout=True)



if __name__ == '__main__':
    unittest.main()
