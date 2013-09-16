# Copyright (C) 2013 Che-Liang Chiou.

'''Itanium C++ ABI of C++ external names (a.k.a. mangling)'''

from cbind.cindex import CursorKind, TypeKind
from pycbind.compatibility import StringIO


# TODO(clchiou): Complete mangle BNF.


def mangle(tree):
    '''Mangle tree node.'''
    output = StringIO()
    _mangled_name(tree, output)
    return output.getvalue()


def _mangled_name(tree, output):
    '''<mangled-name> ::= _Z <encoding>'''
    output.write('_Z')
    _encoding(tree, output)


def _encoding(tree, output):
    '''<encoding> ::= <function name> <bare-function-type>
                  ::= <data name>
                  ::= <special-name>
    '''
    if tree.kind == CursorKind.FUNCTION_DECL:
        _name(tree, output)
        _bare_function_type(tree, output, mangle_return_type=False)
    else:
        _name(tree, output)


def _name(tree, output):
    '''<name> ::= <nested-name>
              ::= <unscoped-name>
              ::= <unscoped-templated-name> <template-args>
              ::= <local-name>
    '''
    parent = tree.semantic_parent
    if (parent.kind == CursorKind.TRANSLATION_UNIT or _is_std_namespace(tree)):
        _unscoped_name(tree, output)
        return
    _nested_name(tree, output)


def _unscoped_name(tree, output):
    '''<unscoped-name> ::= <unqualified-name>
                       ::= St <unqualified-name>    # ::std::
    '''
    if _is_std_namespace(tree):
        output.write('St')
    _unqualified_name(tree, output)


def _nested_name(tree, output):
    '''<nested-name> ::= N [<CV-qualifiers>] [<ref-qualifier>]
                         <prefix> <unqualified-name> E
                     ::= N [<CV-qualifiers>] [<ref-qualifier>]
                         <template-prefix> <template-args> E
    '''
    output.write('N')
    _cv_qualifiers(tree.type, output)
    _ref_qualifier(tree.type, output)
    _prefix(tree, output)
    _unqualified_name(tree, output)
    output.write('E')


def _prefix(tree, output):
    '''<prefix> ::= <prefix> <unqualified-name>
                ::= <template-prefix> <template-args>
                ::= <template-param>
                ::= <decltype>
                ::= # empty
                ::= <substitution>
                ::= <prefix> <data-member-prefix>
    '''
    if (tree.semantic_parent.kind == CursorKind.NAMESPACE or
            tree.semantic_parent.kind == CursorKind.CLASS_DECL):
        _prefix(tree.semantic_parent, output)
        _unqualified_name(tree.semantic_parent, output)


def _unqualified_name(tree, output):
    '''<unqualified-name> ::= <operator-name>
                          ::= <ctor-dtor-name>
                          ::= <source-name>
                          ::= <unnamed-type-name>
    '''
    _source_name(tree, output)


def _source_name(tree, output):
    '''<source-name> ::= <positive length number> <identifier>'''
    assert tree.spelling
    output.write('%d%s' % (len(tree.spelling), tree.spelling))


BUILTIN_TYPE_MAP = {
        TypeKind.VOID:              'v',
        TypeKind.BOOL:              'b',
        TypeKind.CHAR_U:            'h',
        TypeKind.UCHAR:             'h',
        TypeKind.CHAR16:            'Ds',
        TypeKind.CHAR32:            'Di',
        TypeKind.USHORT:            't',
        TypeKind.UINT:              'j',
        TypeKind.ULONG:             'm',
        TypeKind.ULONGLONG:         'y',
        TypeKind.UINT128:           'o',
        TypeKind.CHAR_S:            'c',
        TypeKind.SCHAR:             'a',
        TypeKind.WCHAR:             'w',
        TypeKind.SHORT:             's',
        TypeKind.INT:               'i',
        TypeKind.LONG:              'l',
        TypeKind.LONGLONG:          'x',
        TypeKind.INT128:            'n',
        TypeKind.FLOAT:             'f',
        TypeKind.DOUBLE:            'd',
        TypeKind.LONGDOUBLE:        'e',
}


def _type(type_, output):
    '''<type> ::= <builtin-type>
              ::= <function-type>
              ::= <class-enum-type>
              ::= <array-type>
              ::= <pointer-to-member-type>
              ::= <template-param>
              ::= <template-template-param> <template-args>
              ::= <decltype>
              ::= <substitution>    # See Compression below

       <type> ::= <CV-qualifiers> <type>
              ::= P <type>  # pointer-to
              ::= R <type>  # reference-to
              ::= O <type>  # rvalue reference-to (C++0x)
              ::= C <type>  # complex pair (C 2000)
              ::= G <type>  # imaginary (C 2000)
              ::= U <source-name> <type>    # vendor extended type qualifier
       <builtin-type> ::= v     # void
                      ::= w     # wchar_t
                      ::= b     # bool
                      ::= c     # char
                      ::= a     # signed char
                      ::= h     # unsigned char
                      ::= s     # short
                      ::= t     # unsigned short
                      ::= i     # int
                      ::= j     # unsigned int
                      ::= l     # long
                      ::= m     # unsigned long
                      ::= x     # long long, __int64
                      ::= y     # unsigned long long, __int64
                      ::= n     # __int128
                      ::= o     # unsigned __int128
                      ::= f     # float
                      ::= d     # double
                      ::= e     # long double, __float80
                      ::= g     # __float128
                      ::= z     # ellipsis
                      ::= Dd    # IEEE 754r decimal floating point (64 bits)
                      ::= De    # IEEE 754r decimal floating point (128 bits)
                      ::= Df    # IEEE 754r decimal floating point (32 bits)
                      ::= Dh
                          # IEEE 754r half-precision floating point (16 bits)
                      ::= Di    # char32_t
                      ::= Ds    # char16_t
                      ::= Da    # auto
                      ::= Dc    # decltype(auto)
                      ::= Dn    # std::nullptr_t (i.e., decltype(nullptr))
                      ::= u <source-name>   # vendor extended type
    '''
    _cv_qualifiers(type_, output)
    while True:
        if type_.kind == TypeKind.POINTER:
            output.write('P')
            type_ = type_.get_pointee()
        else:
            break
    if type_.kind in BUILTIN_TYPE_MAP:
        output.write(BUILTIN_TYPE_MAP[type_.kind])


def _cv_qualifiers(type_, output):
    '''<CV-qualifiers> ::= [r] [V] [K]  # restrict (C99), volatile, const'''
    pass


def _ref_qualifier(type_, output):
    '''<ref-qualifier> ::= R    # & ref-qualifier
                       ::= O    # && ref-qualifier
    '''
    pass


def _bare_function_type(tree, output, mangle_return_type):
    '''<bare-function-type> ::= <signature type>+
       # types are possible return type, then parameter types
    '''
    if mangle_return_type:
        _type(tree.result_type, output)
    if tree.get_num_arguments() == 0 and not tree.type.is_function_variadic():
        output.write('v')
    else:
        for arg in tree.get_arguments():
            _type(arg.type, output)
        if tree.type.is_function_variadic():
            output.write('z')


def _is_std_namespace(tree):
    '''Check if it is declared in std namespace.'''
    while tree:
        if tree.kind == CursorKind.NAMESPACE and tree.spelling == 'std':
            return True
        tree = tree.semantic_parent
    return False
