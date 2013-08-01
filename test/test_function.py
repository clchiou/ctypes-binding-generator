import unittest
import helper


class TestFunction(helper.TestCtypesBindingGenerator):

    def test_simple_function(self):
        self.run_test('''
int foo(int);
        ''', '''
foo = _lib.foo
foo.argtypes = [c_int]
foo.restype = c_int
        ''')

    def test_no_arg(self):
        self.run_test('''
int foo(void);
        ''', '''
foo = _lib.foo
foo.restype = c_int
        ''')

    def test_pointer_arg(self):
        self.run_test('''
void foo(int *, char *, wchar_t *, void *);
        ''', '''
foo = _lib.foo
foo.argtypes = [POINTER(c_int), c_char_p, POINTER(c_int), c_void_p]
        ''')

    def test_variadic(self):
        self.run_test('''
int printf(const char *, ...);
        ''', '''
printf = _lib.printf
printf.restype = c_int
        ''')

    def test_array_arg(self):
        self.run_test('''
void foo(int bar[3]);
        ''', '''
foo = _lib.foo
foo.argtypes = [(c_int * 3)]
        ''')

    def test_incomplete_array_arg(self):
        self.run_test('''
void spam(int egg[]);
        ''', '''
spam = _lib.spam
spam.argtypes = [POINTER(c_int)]
        ''')

    def test_funcptr_arg(self):
        self.run_test('''
void foo(void (*bar)(int spam[3]));
        ''', '''
foo = _lib.foo
foo.argtypes = [CFUNCTYPE(None, POINTER(c_int))]
        ''')

    def test_function_body(self):
        self.run_test('''
int square(int x)
{
    int y = x * x;
    return y;
}
        ''', '''
square = _lib.square
square.argtypes = [c_int]
square.restype = c_int
        ''')

    def test_static_function(self):
        self.run_test('''
static void foo(void);
static inline int bar(void) { return 0; }
        ''', '''
        ''')

    def test_enum_return_type(self):
        self.run_test('''
enum X {
    x = 0
};

enum X foo(void);
        ''', '''
X = c_uint
x = 0

foo = _lib.foo
foo.restype = X
        ''')


if __name__ == '__main__':
    unittest.main()
