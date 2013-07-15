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

    # TODO(clchiou): Reenable this test when libclang exposes IncompleteArray.
    def disable_test_incomplete_array_arg(self):
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


if __name__ == '__main__':
    unittest.main()
