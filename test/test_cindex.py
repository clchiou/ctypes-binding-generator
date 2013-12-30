import os
import tempfile
import unittest

import helper
import cbind
from cbind.ctypes_binding import CtypesBindingGenerator
from cbind.source import SyntaxTree, SyntaxTreeType


class TestCIndex(helper.TestCtypesBindingGenerator):

    def test_syntax_error(self):
        with self.assertRaises(SyntaxError):
            self.run_test('''
int foo(,);
            ''', '''
            ''')

    def test_syntax_tree(self):
        class FakeCursor:
            class FakeLocation:
                class FakeFile:
                    name = 'filename'
                file = FakeFile()
                offset = 1

            def __init__(self):
                self.spelling = 'spelling'
                self.location = FakeCursor.FakeLocation()
                self.kind = 'kind'

        cursor1 = FakeCursor()
        cursor2 = FakeCursor()
        cursor3 = FakeCursor()
        cursor3.spelling = 'XXX'
        t1 = SyntaxTree(cursor1, None, None)
        t2 = SyntaxTree(cursor2, None, None)
        t3 = SyntaxTree(cursor3, None, None)

        self.assertTrue(t1 == t2)
        self.assertFalse(t1 != t2)

        self.assertFalse(t1 == t3)
        self.assertTrue(t1 != t3)

    def test_syntax_tree_type(self):
        t1 = SyntaxTreeType(None, None)
        t2 = SyntaxTreeType(None, None)
        with self.assertRaises(AttributeError):
            t1 == t2
        with self.assertRaises(AttributeError):
            t1 != t2
        with self.assertRaises(AttributeError):
            t1.xxx

    def test_file(self):
        c_file = os.path.join(os.path.dirname(__file__), 'file.c')
        cbgen = CtypesBindingGenerator()
        cbgen.parse(c_file)


class TestMain(unittest.TestCase):

    def setUp(self):
        self.input_path = tempfile.mkstemp(suffix='.c')[1]
        self.output_path = tempfile.mkstemp(suffix='.py')[1]

    def tearDown(self):
        os.remove(self.input_path)
        os.remove(self.output_path)

    def test_main(self):
        with open(self.input_path, 'w') as fin:
            fin.write('''
#define Y X + 1

enum {
    number = Y,
};
            ''')
        args = ('--enable-macro -i %s -o %s -- -DX=1' %
                (self.input_path, self.output_path)).split()
        cbind.main(args=args)


if __name__ == '__main__':
    unittest.main()
