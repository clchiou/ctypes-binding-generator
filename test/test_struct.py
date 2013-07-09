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

    def test_empty_struct(self):
        self.run_test('''
struct foo {};
        ''', '''
class foo(Structure):
    pass
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

    def test_self_reference(self):
        self.run_test('''
struct blob {
    struct blob *bp;
    int i;
};
        ''', '''
class blob(Structure):
    _pack_ = 8
    _fields_ = [('bp', POINTER(blob)),
                ('i', c_int)]
        ''')

    def test_anonymous_struct(self):
        self.run_test('''
struct foo {
    struct {
        int i;
    } s;
};
        ''', '''
class _anonymous_struct_0001(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

class foo(Structure):
    _anonymous_ = ('s',)
    _pack_ = 4
    _fields_ = [('s', _anonymous_struct_0001)]
        ''')

    def test_bitfield(self):
        self.run_test('''
struct foo {
    int i : 1;
    int j : 31;
};
        ''', '''
class foo(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int, 1),
                ('j', c_int, 31)]
        ''')

    def test_cross_reference(self):
        self.run_test('''
struct blob1;

struct blob2 {
    struct blob1 *b1;
};

struct blob1 {
    struct blob2 *b2;
};
        ''', '''
class blob1(Structure):
    pass

class blob2(Structure):
    _pack_ = 8
    _fields_ = [('b1', POINTER(blob1))]

blob1._pack_ = 8
blob1._fields_ = [('b2', POINTER(blob2))]
        ''')


if __name__ == '__main__':
    unittest.main()
