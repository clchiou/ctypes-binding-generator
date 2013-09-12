import unittest
import helper
import cbind.ctypes_binding


def check_yaml():
    try:
        import yaml
    except ImportError:
        return False
    else:
        return True


class TestConfig(helper.TestCtypesBindingGenerator):

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_empty_rule(self):
        self.run_test('''
enum {
    X = 1
};
        ''', '''
        ''', config='''
import:
    - import: True
        ''')

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

void func_3(void);
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

func_3 = _lib.func_3
        ''', config='''
import:
    - name: ^func_([12])$
    - restype: None
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

        self.run_test('''
enum { A, B, C };
        ''', '''
B = 1
C = 2
        ''', config='''
import:
    - name: A
      import: False
    - name: '[ABC]'
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
      rename: \1
        ''')

        self.run_test('''
int Prefix_HelloWorld = 1;
        ''', '''
HELLO_WORLD = c_int.in_dll(_lib, 'Prefix_HelloWorld')
        ''', config=r'''
rename:
    - name: Prefix_
      rename:
        - pattern: 'Prefix_'
          replace: ''
        - pattern: '([a-z])([A-Z])'
          replace: \1_\2
        - pattern: (.*)
          function: 'lambda match: match.group(1).upper()'
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
    def test_errcheck(self):
        self.run_test('''
struct foo {
    int i;
};

struct foo func(void);

struct foo no_errcheck(void);
        ''', '''
class foo(Structure):
    pass
foo._fields_ = [('i', c_int)]

func = _lib.func
func.restype = foo
func.errcheck = errcheck_func

no_errcheck = _lib.no_errcheck
no_errcheck.restype = foo
        ''', config='''
errcheck:
    - name: no_errcheck
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

void not_method_1(struct foo*, int i);

void not_method_2(struct foo);
        ''', cbind.ctypes_binding.METHOD_DESCRIPTOR + '''
class foo(Structure):
    pass

bar = _lib.bar
bar.argtypes = [POINTER(foo)]
foo.method_bar = _CtypesFunctor(bar)

not_method_1 = _lib.not_method_1
not_method_1.argtypes = [POINTER(foo), c_int]

not_method_2 = _lib.not_method_2
not_method_2.argtypes = [foo]
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

enum bar {
    X = 1
};
        ''', '''
class foo(MixinFoo1, MixinFoo2, Structure):
    pass

class bar(MixinBar, c_uint):
    pass
X = 1
        ''', config='''
mixin:
    - name: foo
      mixin: [MixinFoo1, MixinFoo2]
    - name: bar
      mixin: [MixinBar]
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_enum(self):
        self.run_test('''
enum {
    X = 1,
    Y = 2,
};

enum my_type {
    W = 1,
    Z = 2,
};
        ''', '''
foo.X = func(1)
foo.Y = func(2)

class my_type(c_uint):
    pass
my_type.W = c_uint(1)
my_type.Z = c_uint(2)
        ''', config='''
enum:
    - name: '[XY]'
      enum: 'foo.{enum_field} = func({enum_value})'
    - parent: {name: my_type}
      enum: '{enum_name}.{enum_field} = {enum_type}({enum_value})'
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_config_order(self):
        self.run_test('''
enum {
    X = 1,
    Y = 2,
    UNCHANGED = 3,
};
        ''', '''
Z = 1
Y = 2
UNCHANGED = 3
        ''', config=r'''
import:
    - name: '[XY]|UNCHANGED'
rename:
    - name: X
      rename: Z
    - name: (UNCHANGED)
      rename: \1
        ''')

        self.run_test('''
enum {
    X = 1,
    Y = 2,
};
        ''', '''
Z = u_int(1)
Y = u_int(2)
        ''', config='''
rename:
    - name: X
      rename: Z
enum:
    - name: '[XY]'
      enum: '{enum_field} = u_int({enum_value})'
        ''')


if __name__ == '__main__':
    unittest.main()
