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
    def test_config(self):
        self.run_test('''
        ''', '''
        ''', config='''
        ''')


if __name__ == '__main__':
    unittest.main()
