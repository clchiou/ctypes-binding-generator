import unittest
import helper


class TestClass(helper.TestCtypesBindingGenerator):

    def test_class(self):
        self.run_test('''
class foo {
  private:
    int i;
  protected:
    int j;
  public:
    int k;
  protected:
    int l;
  private:
    int m;
};

typedef class {
  private:
    int x;
} bar;
        ''', '''
class foo(Structure):
    pass
foo._fields_ = [('i', c_int),
                ('j', c_int),
                ('k', c_int),
                ('l', c_int),
                ('m', c_int)]

class bar(Structure):
    pass
bar._fields_ = [('x', c_int)]
        ''', filename='input.cpp')

    def test_method(self):
        self.run_test('''
struct cls {
  public:
    int memb;
    int method1(char);
    virtual void vmethod(void);
    static int smethod(char);
};
        ''', '''
class cls(Structure):
    pass
cls._fields_ = [('__python_struct_padding', c_char * 8),
                ('memb', c_int)]

cls.method1 = _lib._ZN3cls7method1Ec
cls.method1.argtypes = [c_char]
cls.method1.restype = c_int
cls.method1 = _CtypesFunctor(cls.method1)

cls.vmethod = _lib._ZN3cls7vmethodEv
cls.vmethod = _CtypesFunctor(cls.vmethod)

cls.smethod = _lib._ZN3cls7smethodEc
cls.smethod.argtypes = [c_char]
cls.smethod.restype = c_int
cls.smethod = staticmethod(cls.smethod)

assert cls.memb.offset == 8, 'cls.memb.offset == 8'
        ''', filename='input.cpp', enable_cpp=True, assert_layout=True)


class TestMangler(helper.TestCppMangler):

    def test_mangler(self):
        self.run_test('''
class cls {
  public:
    cls();
    ~cls();
    static int smemb1;
    void membf1() & {}
    void membf2() && {}
    const cls &operator+(const cls &);
};

namespace space {
class cls {
  public:
    static int smemb2;
};
}

namespace std {
void func_std_ns(void);
}

void func1(void);
int func2(char *, ...);
void func3(float *, short &, double _Complex, const volatile long*);
enum enum1 {
    X
};
void func4(cls, enum1);
void func5(void (*)());
void func6(void (cls::*)());
        ''',
        [({'name': 'cls', 'kind': ['CONSTRUCTOR']}, '_ZN3clsC1Ev'),
         ('~cls', '_ZN3clsD1Ev'),
         ('smemb1', '_ZN3cls6smemb1E'),
         ('smemb2', '_ZN5space3cls6smemb2E'),
         ('operator\+', '_ZN3clsplERKS_'),
         ('membf1', '_ZNR3cls6membf1Ev'),
         ('membf2', '_ZNO3cls6membf2Ev'),
         ('func_std_ns', '_ZSt11func_std_nsv'),
         ('func1', '_Z5func1v'),
         ('func2', '_Z5func2Pcz'),
         ('func3', '_Z5func3PfRsCdPVKl'),
         ('func4', '_Z5func43cls5enum1'),
         ('func5', '_Z5func5PFvvE'),
         ('func6', '_Z5func6M3clsFvvE'),
        ], args=['-std=c++11'])


if __name__ == '__main__':
    unittest.main()
