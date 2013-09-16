# Copyright (C) 2013 Che-Liang Chiou.

'''Itanium C++ ABI of C++ external names (a.k.a. mangling)'''

from cbind.cindex import CursorKind
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
    _name(tree, output)


def _name(tree, output):
    '''<name> ::= <nested-name>
              ::= <unscoped-name>
              ::= <unscoped-templated-name> <template-args>
              ::= <local-name>
    '''
    _nested_name(tree, output)


def _nested_name(tree, output):
    '''<nested-name> ::= N [<CV-qualifiers>] [<ref-qualifier>]
                         <prefix> <unqualified-name> E
                     ::= N [<CV-qualifiers>] [<ref-qualifier>]
                         <template-prefix> <template-args> E
    '''
    output.write('N')
    _cv_qualifiers(tree, output)
    _ref_qualifier(tree, output)
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


def _cv_qualifiers(tree, output):
    '''<CV-qualifiers> ::= [r] [V] [K]  # restrict (C99), volatile, const'''
    pass


def _ref_qualifier(tree, output):
    '''<ref-qualifier> ::= R  # & ref-qualifier
                       ::= O  # && ref-qualifier
    '''
    pass
