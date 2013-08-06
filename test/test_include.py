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

    def test_simple_header(self):
        self.run_header_test('''
struct blob1 {
    int i;
};

struct blob2 {
    struct blob1 *bp1;
};
        ''', '''
#include "%s"

struct blob2 b2;
        ''', '''
class blob1(Structure):
    pass
blob1._pack_ = 4
blob1._fields_ = [('i', c_int)]

class blob2(Structure):
    pass
blob2._pack_ = 8
blob2._fields_ = [('bp1', POINTER(blob1))]

b2 = blob2.in_dll(_lib, 'b2')
        ''')

    def test_self_reference(self):
        self.run_header_test('''
struct blob {
    struct blob *bp;
};
        ''', '''
#include "%s"

struct blob b;
        ''', '''
class blob(Structure):
    pass

blob._pack_ = 8
blob._fields_ = [('bp', POINTER(blob))]

b = blob.in_dll(_lib, 'b')
        ''')

    def test_function(self):
        self.run_header_test('''
typedef struct {
    int i;
} my_blob;
        ''', '''
#include "%s"
my_blob foo(my_blob);
        ''', '''
class my_blob(Structure):
    pass
my_blob._pack_ = 4
my_blob._fields_ = [('i', c_int)]

foo = _lib.foo
foo.argtypes = [my_blob]
foo.restype = my_blob
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
class other_type(Structure):
    pass
other_type._pack_ = 4
other_type._fields_ = [('i', c_int)]

my_type = other_type

x = other_type.in_dll(_lib, 'x')
        ''')

    def test_enum(self):
        self.run_header_test('''
enum my_enum {
    X,
    Y,
};
        ''', '''
#include "%s"
enum my_enum x;
        ''', '''
my_enum = c_uint
X = 0
Y = 1

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
    pass
other_struct._pack_ = 4
other_struct._fields_ = [('i', c_int)]

class my_struct(Structure):
    pass
my_struct._pack_ = 4
my_struct._fields_ = [('o', other_struct)]
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
    pass
blob2._pack_ = 4
blob2._fields_ = [('i', c_int)]

class blob1(Structure):
    pass
blob1._pack_ = 4
blob1._fields_ = [('b2', blob2)]

class _anonymous_struct_0001(Structure):
    pass
_anonymous_struct_0001._pack_ = 4
_anonymous_struct_0001._fields_ = [('j', c_int)]

class blob3(Structure):
    pass
blob3._anonymous_ = ('b',)
blob3._pack_ = 4
blob3._fields_ = [('b', _anonymous_struct_0001)]

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
    pass
my_blob._pack_ = 4
my_blob._fields_ = [('i', c_int)]

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
class my_blob(Structure):
    pass
my_blob._pack_ = 4
my_blob._fields_ = [('i', c_int)]

class foo(Structure):
    pass

foo._pack_ = 4
foo._fields_ = [('blob', my_blob)]
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
    pass
blob_1._pack_ = 4
blob_1._fields_ = [('i', c_int)]

class blob_2(Structure):
    pass
blob_2._pack_ = 4
blob_2._fields_ = [('b1', blob_1)]

b2 = blob_2.in_dll(_lib, 'b2')
        ''')

    def test_forward_decl(self):
        self.run_headers_test('''
struct blob {
    int i;
};
        ''', '''
#include "%(header_0)s"

struct foo {
    struct blob *bp;
};
        ''', '''
struct foo;

#include "%(header_1)s"

struct foo f;
        ''', '''
class foo(Structure):
    pass

class blob(Structure):
    pass
blob._pack_ = 4
blob._fields_ = [('i', c_int)]

foo._pack_ = 8
foo._fields_ = [('bp', POINTER(blob))]

f = foo.in_dll(_lib, 'f')
        ''')


if __name__ == '__main__':
    unittest.main()
