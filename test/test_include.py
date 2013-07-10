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

    def test_nested_struct(self):
        self.run_header_test('''
struct blob1 {
    struct blob2 {
        int i;
    } b2;
};

struct blob3 {
    struct {
        int j;
    } b;
};
        ''', '''
#include "%s"

struct blob1 var_b1;
struct blob3 var_b3;
        ''', '''
class blob2(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

class blob1(Structure):
    _pack_ = 4
    _fields_ = [('b2', blob2)]

class _anonymous_struct_0001(Structure):
    _pack_ = 4
    _fields_ = [('j', c_int)]

class blob3(Structure):
    _anonymous_ = ('b',)
    _pack_ = 4
    _fields_ = [('b', _anonymous_struct_0001)]

var_b1 = blob1.in_dll(_lib, 'var_b1')
var_b3 = blob3.in_dll(_lib, 'var_b3')
        ''')

    def test_struct_var(self):
        self.run_header_test('''
struct my_blob {
    int i;
};
        ''', '''
#include "%s"
struct my_blob b;
        ''', '''
class my_blob(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

b = my_blob.in_dll(_lib, 'b')
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
    pass

foo._pack_ = 4
foo._fields_ = [('blob', _anonymous_struct_0001)]
        ''')


class TestNestedInclude(helper.TestCtypesBindingGenerator):

    def run_headers_test(self, *args):
        header_codes, c_code, python_code = args[:-2], args[-2], args[-1]
        header_paths = []
        header_info = {}
        try:
            for i in xrange(len(header_codes)):
                _, header_path = tempfile.mkstemp(suffix='.h')
                header_paths.append(header_path)
                header_info['header_%d' % i] = header_path
            for header_path, header_code in zip(header_paths, header_codes):
                with open(header_path, 'w') as header_file:
                    header_file.write(header_code % header_info)
            self.run_test(c_code % header_info, python_code)
        finally:
            for header_path in header_paths:
                os.remove(header_path)

    def test_nested_include(self):
        self.run_headers_test('''
struct blob_1 {
    int i;
};
        ''', '''
#include "%(header_0)s"

struct blob_2 {
    struct blob_1 b1;
};
        ''', '''
#include "%(header_1)s"

struct blob_2 b2;
        ''', '''
class blob_1(Structure):
    _pack_ = 4
    _fields_ = [('i', c_int)]

class blob_2(Structure):
    _pack_ = 4
    _fields_ = [('b1', blob_1)]

b2 = blob_2.in_dll(_lib, 'b2')
        ''')


if __name__ == '__main__':
    unittest.main()
