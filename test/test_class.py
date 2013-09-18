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
        ''',
        [({'name': 'cls', 'kind': ['CONSTRUCTOR']}, '_ZN3clsC1Ev'),
         ('~cls', '_ZN3clsD1Ev'),
         ('smemb1', '_ZN3cls6smemb1E'),
         ('smemb2', '_ZN5space3cls6smemb2E'),
         # TODO: ref-qualifier is not exposed through libclang.
         #('membf1', '_ZNR3cls6membf1Ev'),
         #('membf2', '_ZNO3cls6membf2Ev'),
         ('func_std_ns', '_ZSt11func_std_nsv'),
         ('func1', '_Z5func1v'),
         ('func2', '_Z5func2Pcz'),
         ('func3', '_Z5func3PfRsCdPVKl')],
        args=['-std=c++11'])


if __name__ == '__main__':
    unittest.main()
