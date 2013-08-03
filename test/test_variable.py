import unittest
import helper


class TestVariable(helper.TestCtypesBindingGenerator):

    def test_simple_variable(self):
        self.run_test('''
extern int i;
        ''', '''
i = c_int.in_dll(_lib, 'i')
        ''')

    def test_pointer(self):
        self.run_test('''
extern int *i;
extern char *c;
extern void *p;
extern unsigned char *uc;
        ''', '''
i = POINTER(c_int).in_dll(_lib, 'i')
c = c_char_p.in_dll(_lib, 'c')
p = c_void_p.in_dll(_lib, 'p')
uc = POINTER(c_ubyte).in_dll(_lib, 'uc')
        ''')

    def test_array(self):
        self.run_test('''
int array[5];
int array2[3][4][5];
        ''', '''
array = (c_int * 5).in_dll(_lib, 'array')
array2 = (((c_int * 5) * 4) * 3).in_dll(_lib, 'array2')
        ''')

    def test_funcptr(self):
        self.run_test('''
enum X {
    x = 0
};

void (*foo)(void);
void (*bar)(char *fmt, ...);
enum X (*spam)(void);
        ''', '''
X = c_uint
x = 0

foo = CFUNCTYPE(None).in_dll(_lib, 'foo')
bar = c_void_p.in_dll(_lib, 'bar')
spam = CFUNCTYPE(X).in_dll(_lib, 'spam')
        ''')


if __name__ == '__main__':
    unittest.main()
