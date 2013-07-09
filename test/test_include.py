import os
import tempfile
import unittest
import helper


class TestInclude(helper.TestCtypesBindingGenerator):

    def setUp(self):
        self.header_fd, self.header_path = tempfile.mkstemp(suffix='.h')

    def tearDown(self):
        os.remove(self.header_path)

    def run_header_test(self, header_code, c_code, python_code):
        with os.fdopen(self.header_fd, 'w') as header_file:
            header_file.write(header_code)
        self.run_test(c_code % self.header_path, python_code)

    def test_function(self):
        self.run_header_test('''
typedef struct {
    int i;
} my_blob;
        ''', '''
#include "%s"
my_blob foo(my_blob);
        ''', '''
class _anonymous_struct_0001(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

foo = _lib.foo
foo.argtypes = [_anonymous_struct_0001]
foo.restype = _anonymous_struct_0001
        ''')

    def test_typedef(self):
        self.run_header_test('''
typedef struct {
    int i;
} other_type;

typedef struct {
    char c;
} some_other_type;
        ''', '''
#include "%s"
typedef other_type my_type;
my_type x;
        ''', '''
class _anonymous_struct_0001(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

my_type = _anonymous_struct_0001

x = _anonymous_struct_0001.in_dll(_lib, 'x')
        ''')

    def test_enum(self):
        self.run_header_test('''
enum my_enum {
    X,
    Y,
};
        ''', '''
#include "%s"
my_enum x;
        ''', '''
my_enum = c_uint
X = my_enum(0)
Y = my_enum(1)

x = my_enum.in_dll(_lib, 'x')
        ''')

    def test_struct(self):
        self.run_header_test('''
struct other_struct {
    int i;
};
        ''', '''
#include "%s"
struct my_struct {
    struct other_struct o;
};
        ''', '''
class other_struct(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

class my_struct(Structure):
    _pack_ = 4
    _fields_ = [('o', other_struct)]
        ''')

    def test_forward_decl(self):
        self.run_header_test('''
typedef struct {
    int i;
} my_blob;
        ''', '''
#include "%s"

struct foo;

struct foo {
    my_blob blob;
};
        ''', '''
class _anonymous_struct_0001(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

class foo(Structure):
    _pack_ = 4
    _fields_ = [('blob', _anonymous_struct_0001)]
        ''')


if __name__ == '__main__':
    unittest.main()
