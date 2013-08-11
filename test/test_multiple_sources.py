import unittest
import helper


class TestMultipleSources(helper.TestCtypesBindingGenerator):

    def test_multiple_define(self):
        self.run_test([('/a/b/c/src.c', '''
typedef struct {
    int bar;
} foo;

void func1(foo);
        '''), ('/d/e/f/src.c', '''
typedef struct {
    int bar;
} foo;

void func2(foo);
        ''')], '''
class foo(Structure):
    pass
foo._fields_ = [('bar', c_int)]

func1 = _lib.func1
func1.argtypes = [foo]

func2 = _lib.func2
func2.argtypes = [foo]
        ''')


if __name__ == '__main__':
    unittest.main()
