import unittest
import helper


def check_yaml():
    try:
        import yaml
    except ImportError:
        return False
    else:
        return True


class TestConfig(helper.TestCtypesBindingGenerator):

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_import(self):
        self.run_test('''
enum Enum {
    X = 1,
    Y = 2,
    XY = 3,
    YX = 4,
};

struct struct_1 {
    int X;
};
        ''', '''
class Enum(c_uint):
    pass
X = 1

class struct_1(Structure):
    pass
struct_1._fields_ = [('X', c_int)]
        ''', config='''
import:
    - name: ^X$
        ''')

        self.run_test('''
struct struct_1 {
    int int_field;
};

struct struct_2 {
    int int_field;
};

void func_1(struct struct_1 *);
struct struct_2 *func_2(void);
        ''', '''
class struct_1(Structure):
    pass
struct_1._fields_ = [('int_field', c_int)]

class struct_2(Structure):
    pass
struct_2._fields_ = [('int_field', c_int)]

func_1 = _lib.func_1
func_1.argtypes = [POINTER(struct_1)]

func_2 = _lib.func_2
func_2.restype = POINTER(struct_2)
        ''', config='''
import:
    - name: ^func_([12])$
        ''')

        self.run_test('''
struct struct_1 {
    int int_field;
};

struct struct_2 {
    struct struct_1 struct_field;
};
        ''', '''
class struct_1(Structure):
    pass
struct_1._fields_ = [('int_field', c_int)]

class struct_2(Structure):
    pass
struct_2._fields_ = [('struct_field', struct_1)]
        ''', config='''
import:
    - name: ^struct_2$
        ''')

        self.run_test('''
struct struct_1 {
    int int_field;
};

typedef struct struct_1 alias_type;
        ''', '''
class struct_1(Structure):
    pass
struct_1._fields_ = [('int_field', c_int)]

alias_type = struct_1
        ''', config='''
import:
    - name: ^alias_type$
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_rename(self):
        self.run_test('''
enum {
    long_long_name_X = 1,
    long_long_name_XY = 2,
};

void long_long_name_XYZ(void);

int long_long_name_XYZW;
        ''', '''
X = 1
XY = 2

XYZ = _lib.long_long_name_XYZ

XYZW = c_int.in_dll(_lib, 'long_long_name_XYZW')
        ''', config=r'''
rename:
    - name: long_long_name_(X)
      rewrite: \1
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_preamble(self):
        self.run_test('''
        ''', '''
import types as __python_types
        ''', config='''
preamble: import types as __python_types
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_preamble(self):
        self.run_test('''
struct foo {
    int i;
};

struct foo func(void);
        ''', '''
class foo(Structure):
    pass
foo._fields_ = [('i', c_int)]

func = _lib.func
func.restype = foo
func.errcheck = errcheck_func
        ''', config='''
errcheck:
    - restype: foo
      errcheck: errcheck_func
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_method(self):
        self.run_test('''
struct foo {
};

void bar(struct foo*);
        ''', '''
import types as _python_types

class foo(Structure):
    pass

bar = _lib.bar
bar.argtypes = [POINTER(foo)]
foo.method_bar = _python_types.MethodType(bar, None, foo)
        ''', config='''
method:
    - argtypes: [POINTER\(foo\)]
      method: foo.method_bar
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_mixin(self):
        self.run_test('''
struct foo {
};
        ''', '''
class foo(MixinFoo1, MixinFoo2, Structure):
    pass
        ''', config='''
mixin:
    - name: foo
      mixin: [MixinFoo1, MixinFoo2]
        ''')


if __name__ == '__main__':
    unittest.main()
