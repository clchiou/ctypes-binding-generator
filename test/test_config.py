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


if __name__ == '__main__':
    unittest.main()
