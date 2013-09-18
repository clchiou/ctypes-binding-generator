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
    if (tree.kind == CursorKind.FUNCTION_DECL or
            tree.kind == CursorKind.CONSTRUCTOR or
            tree.kind == CursorKind.DESTRUCTOR):
        _name(tree, output)
        _bare_function_type(tree, output, mangle_return_type=False)
    elif _is_special_entity(tree):
        _special_name(tree, output)
    else:
        _name(tree, output)


def _name(tree, output):
    '''<name> ::= <nested-name>
              ::= <unscoped-name>
              ::= <unscoped-templated-name> <template-args>
              ::= <local-name>
    '''
    if (tree.semantic_parent.kind == CursorKind.TRANSLATION_UNIT or
            _is_std_namespace(tree)):
        _unscoped_name(tree, output)
    elif _is_unscoped_template(tree):
        _unscoped_template_name(tree, output)
        _template_args(tree, output)
    elif _is_local_entity(tree):
        _local_name(tree, output)
    else:
        _nested_name(tree, output)


def _special_name(tree, output):
    '''<special-name> ::= TV <type> # virtual table
                      ::= TT <type> # VTT structure (construction vtable index)
                      ::= TI <type> # typeinfo structure
                      ::= TS <type> # typeinfo name (null-terminated byte string)
    '''
    pass


def _unscoped_name(tree, output):
    '''<unscoped-name> ::= <unqualified-name>
                       ::= St <unqualified-name>    # ::std::
    '''
    if _is_std_namespace(tree):
        output.write('St')
    _unqualified_name(tree, output)


def _unscoped_template_name(tree, output):
    '''<unscoped-template-name> ::= <unscoped-name>
                                ::= <substitution>
    '''
    _unscoped_name(tree, output)


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
                ::= # empty
                ::= <substitution>
    '''
    if (tree.semantic_parent.kind == CursorKind.NAMESPACE or
            tree.semantic_parent.kind == CursorKind.CLASS_DECL):
        _prefix(tree.semantic_parent, output)
        _unqualified_name(tree.semantic_parent, output)
    elif _is_template(tree):
        _template_prefix(tree, output)
        _template_args(tree, output)
    elif _is_template_param(tree):
        _template_param(tree, output)


def _template_prefix(tree, output):
    '''<template-prefix> ::= <prefix> <template unqualified-name>
                         ::= <template-param>
                         ::= <substitution>
    '''
    pass


def _unqualified_name(tree, output):
    '''<unqualified-name> ::= <operator-name>
                          ::= <ctor-dtor-name>
                          ::= <source-name>
    '''
    if tree.kind == CursorKind.CONSTRUCTOR:
        _ctor_name(tree, output)
    elif tree.kind == CursorKind.DESTRUCTOR:
        _dtor_name(tree, output)
    else:
        _source_name(tree, output)


def _source_name(tree, output):
    '''<source-name> ::= <positive length number> <identifier>'''
    assert tree.spelling
    output.write('%d%s' % (len(tree.spelling), tree.spelling))


def _ctor_name(tree, output):
    '''<ctor-dtor-name> ::= C1  # complete object constructor
                        ::= C2  # base object constructor
                        ::= C3  # complete object allocating constructor
                        ::= D0  # deleting destructor
                        ::= D1  # complete object destructor
                        ::= D2  # base object destructor
    '''
    output.write('C1')


def _dtor_name(tree, output):
    '''<ctor-dtor-name> ::= C1  # complete object constructor
                        ::= C2  # base object constructor
                        ::= C3  # complete object allocating constructor
                        ::= D0  # deleting destructor
                        ::= D1  # complete object destructor
                        ::= D2  # base object destructor
    '''
    output.write('D1')


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
    while True:
        # TODO(clchiou): G <type>  # imaginary (C 2000)
        if type_.kind == TypeKind.POINTER:
            output.write('P')
            type_ = type_.get_pointee()
        elif type_.kind == TypeKind.LVALUEREFERENCE:
            output.write('R')
            type_ = type_.get_pointee()
        elif type_.kind == TypeKind.RVALUEREFERENCE:
            output.write('O')
            type_ = type_.get_pointee()
        elif type_.kind == TypeKind.COMPLEX:
            output.write('C')
            type_ = type_.get_element_type()
        else:
            break
    _cv_qualifiers(type_, output)
    if type_.kind in BUILTIN_TYPE_MAP:
        output.write(BUILTIN_TYPE_MAP[type_.kind])
    elif type_.is_user_defined_type():
        _class_enum_type(type_.get_declaration(), output)


def _cv_qualifiers(type_, output):
    '''<CV-qualifiers> ::= [r] [V] [K]  # restrict (C99), volatile, const'''
    # TODO(clchiou): [r]  # restrict (C99)
    if type_.is_volatile_qualified():
        output.write('V')
    if type_.is_const_qualified():
        output.write('K')


def _ref_qualifier(type_, output):
    '''<ref-qualifier> ::= R    # & ref-qualifier
                       ::= O    # && ref-qualifier
    '''
    if type_.kind == TypeKind.FUNCTIONPROTO:
        pass  # TODO: ref-qualifier is not exposed through libclang.


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


def _class_enum_type(tree, output):
    '''<class-enum-type> ::= <name>'''
    _name(tree, output)


def _template_param(tree, output):
    '''<template-param> ::= T_  # first template parameter
                        ::= T <parameter-2 non-negative number> _
    '''
    pass


def _template_args(tree, output):
    '''<template-args> ::= I <template-arg>+ E
       <template-arg>  ::= <type>               # type or template
                       ::= X <expression> E     # expression
                       ::= <expr-primary>       # simple expressions
                       ::= J <template-arg>* E  # argument pack
    '''
    pass


def _local_name(tree, output):
    '''<local-name> := Z <function encoding> E <entity name> [<discriminator>]
                    := Z <function encoding> E s [<discriminator>]
       <discriminator> := _ <non-negative number>
    '''
    pass


def _is_std_namespace(tree):
    '''Check if it is declared in std namespace.'''
    while tree:
        if tree.kind == CursorKind.NAMESPACE and tree.spelling == 'std':
            return True
        tree = tree.semantic_parent
    return False


def _is_special_entity(tree):
    '''Check if it is a special entity.'''
    return False


def _is_local_entity(tree):
    '''Check if it is a local entity.'''
    return False


def _is_unscoped_template(tree):
    '''Check if it is a function or class template.'''
    return False


def _is_template(tree):
    '''Check if it is a function or class template.'''
    return False


def _is_template_param(tree):
    '''Check if it is a function or class template.'''
    return False
