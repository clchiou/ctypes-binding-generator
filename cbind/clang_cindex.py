'''Compatibility layer of libclang cindex module.'''

from ctypes import c_uint
import clang.cindex as _cindex
from clang.cindex import Index, Cursor, CursorKind, Type, TypeKind


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind',
        'clang_getCursorLinkage', 'clang_Cursor_getNumArguments']


# Register libclang function.
_cindex.register_function(_cindex.conf.lib,
        ('clang_getCursorLinkage', [Cursor], c_uint), False)


# pylint: disable=C0103
clang_getCursorLinkage = _cindex.conf.lib.clang_getCursorLinkage
clang_Cursor_getNumArguments = _cindex.conf.lib.clang_Cursor_getNumArguments
