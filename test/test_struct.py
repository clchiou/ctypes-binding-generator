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
    pass
foo._fields_ = [('bar', c_int)]
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
        int i;
    } s;
};
        ''', '''
class foo(Structure):
    pass
foo._fields_ = [('i', c_int)]

class bar(Structure):
    pass
bar._fields_ = [('s', foo)]
        ''')

    def test_self_reference(self):
        self.run_test('''
struct blob {
    struct blob *bp;
    int i;
};
        ''', '''
class blob(Structure):
    pass
blob._fields_ = [('bp', POINTER(blob)),
                 ('i', c_int)]
        ''')

    def test_nested_self_reference(self):
        self.run_test('''
struct blob1 {
    struct blob2 {
        struct blob1 *bp1;
    } b2;
};
        ''', '''
class blob1(Structure):
    pass

class blob2(Structure):
    pass
blob2._fields_ = [('bp1', POINTER(blob1))]

blob1._fields_ = [('b2', blob2)]
        ''')

    def test_anonymous_struct(self):
        self.run_test('''\
struct foo {
    struct {
        int i;
    } s;
};
        ''', '''
class _struct_input_c_2_5(Structure):
    pass
_struct_input_c_2_5._fields_ = [('i', c_int)]

class foo(Structure):
    pass
foo._fields_ = [('s', _struct_input_c_2_5)]
        ''')

    def test_bitfield(self):
        self.run_test('''
struct foo {
    int i : 1;
    int j : 31;
};
        ''', '''
class foo(Structure):
    pass
foo._fields_ = [('i', c_int, 1),
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
    pass
blob2._fields_ = [('b1', POINTER(blob1))]

blob1._fields_ = [('b2', POINTER(blob2))]
        ''')

    def test_name_mangling(self):
        self.run_test('''
struct __foo {
    int i;
};

struct bar{
    struct __foo foo;
};
        ''', '''
class __foo(Structure):
    pass
__foo._fields_ = [('i', c_int)]

class bar(Structure):
    pass
bar._fields_ = [('foo', __foo)]
        ''')

    def test_layout_assertion(self):
        self.run_test('''
struct blob1 {
    int i;
    int j;
};

struct blob2 {
    int i : 1;
    int j : 31;
    int k;
    int l;
    int m : 16;
    int n : 16;
    int o;
};
        ''', '''
class blob1(Structure):
    pass
blob1._fields_ = [('i', c_int),
                  ('j', c_int)]
assert blob1.i.offset == 0, 'blob1.i.offset == 0'
assert blob1.j.offset == 4, 'blob1.j.offset == 4'
class blob2(Structure):
    pass
blob2._fields_ = [('i', c_int, 1),
                  ('j', c_int, 31),
                  ('k', c_int),
                  ('l', c_int),
                  ('m', c_int, 16),
                  ('n', c_int, 16),
                  ('o', c_int)]
assert blob2.i.offset == 0, 'blob2.i.offset == 0'
assert blob2.j.offset == 0, 'blob2.j.offset == 0'
assert blob2.k.offset == 4, 'blob2.k.offset == 4'
assert blob2.l.offset == 8, 'blob2.l.offset == 8'
assert blob2.m.offset == 12, 'blob2.m.offset == 12'
assert blob2.n.offset == 12, 'blob2.n.offset == 12'
assert blob2.o.offset == 16, 'blob2.o.offset == 16'
        ''', assert_layout=True)


if __name__ == '__main__':
    unittest.main()
