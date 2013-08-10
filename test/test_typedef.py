import unittest
import helper


class TestTypedef(helper.TestCtypesBindingGenerator):

    def test_simple_typedef(self):
        self.run_test('''
typedef int my_type;
typedef struct foo bar;
        ''', '''
my_type = c_int

class foo(Structure):
    pass

bar = foo
        ''')

    def test_chained_typedef(self):
        self.run_test('''
typedef struct type_0 type_1;
typedef type_1 type_2;
        ''', '''
class type_0(Structure):
    pass

type_1 = type_0
type_2 = type_0
        ''')

    def test_anonymous_struct_typedef(self):
        self.run_test('''
typedef struct {
    int i;
} type_1;
typedef type_1 type_2;
        ''', '''
class type_1(Structure):
    pass
type_1._fields_ = [('i', c_int)]

type_2 = type_1
        ''')

    def test_forward_decl(self):
        self.run_test('''
struct blob;

struct blob;

typedef struct blob my_blob;

struct blob {
    int i;
};
        ''', '''
class blob(Structure):
    pass

my_blob = blob

blob._fields_ = [('i', c_int)]
        ''')

    def test_typedef_void(self):
        self.run_test('''
typedef void foo;
foo *p;
        ''', '''
p = c_void_p.in_dll(_lib, 'p')
        ''')


if __name__ == '__main__':
    unittest.main()
