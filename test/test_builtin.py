import unittest
import helper


class TestBuiltin(helper.TestCtypesBindingGenerator):

    def test_size_t(self):
        self.run_test('''
#include <stdio.h>
size_t size;
ssize_t ssize;
wchar_t wchar;
wchar_t *wchar_p;
        ''', '''
size = c_size_t.in_dll(_lib, 'size')
ssize = c_ssize_t.in_dll(_lib, 'ssize')
wchar = c_wchar_t.in_dll(_lib, 'wchar')
wchar_p = c_wchar_p.in_dll(_lib, 'wchar_p')
        ''',
        # TODO(clchiou): Search include path.
        args=['-I/usr/local/lib/clang/3.4/include'])


if __name__ == '__main__':
    unittest.main()
