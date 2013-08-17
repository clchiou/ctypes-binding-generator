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

struct foo {
    int X;
};
        ''', '''
class Enum(c_uint):
    pass
X = 1

class foo(Structure):
    pass
foo._fields_ = [('X', c_int)]
        ''', config='''
import: ^X$   # Cherry-pick output
        ''')

    @unittest.skipIf(not check_yaml(), 'require package yaml')
    def test_rename(self):
        self.run_test('''
enum {
    long_long_name_X = 1,
    long_long_name_XY = 2,
};
        ''', '''
X = 1
XY = 2
        ''', config=r'''
rename:
    - [long_long_name_(X), \1]
        ''')


if __name__ == '__main__':
    unittest.main()
