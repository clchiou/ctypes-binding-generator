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
va_list va_list_v;
        ''', '''
class __va_list_tag(Structure):
    pass
__va_list_tag._fields_ = [('gp_offset', c_uint),
                          ('fp_offset', c_uint),
                          ('overflow_arg_area', c_void_p),
                          ('reg_save_area', c_void_p)]

size = c_size_t.in_dll(_lib, 'size')
ssize = c_ssize_t.in_dll(_lib, 'ssize')
wchar = c_wchar_t.in_dll(_lib, 'wchar')
wchar_p = c_wchar_p.in_dll(_lib, 'wchar_p')
va_list_v = (__va_list_tag * 1).in_dll(_lib, 'va_list_v')
        ''',
        # TODO(clchiou): Search include path.
        args=['-I/usr/local/lib/clang/3.4/include'])

    def test_unsupported_type(self):
        with self.assertRaises(TypeError):
            self.run_test('''
__int128_t x = 1;
            ''', '''
            ''')


if __name__ == '__main__':
    unittest.main()
