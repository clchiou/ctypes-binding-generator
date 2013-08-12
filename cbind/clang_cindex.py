'''Compatibility layer of libclang cindex module.'''

from ctypes import c_uint
import clang.cindex as _cindex
from clang.cindex import Index, Cursor, CursorKind, Type, TypeKind


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind', 'LinkageKind']


# Register libclang function.
_cindex.register_function(_cindex.conf.lib,
        ('clang_getCursorLinkage', [Cursor], c_uint), False)


class LinkageKind:  # pylint: disable=R0903
    '''Class represents linkage kind.'''
    _linkage_kind_tags = (
            'INVALID',
            'NO_LINKAGE',
            'INTERNAL',
            'UNIQUE_EXTERNAL',
            'EXTERNAL',
    )

    def __init__(self, kind):
        self.kind = kind

    def __eq__(self, other):
        return self.kind == other.kind

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'LinkageKind.%s' % self._linkage_kind_tags[self.kind]


LinkageKind.INVALID         = LinkageKind(0)
LinkageKind.NO_LINKAGE      = LinkageKind(1)
LinkageKind.INTERNAL        = LinkageKind(2)
LinkageKind.UNIQUE_EXTERNAL = LinkageKind(3)
LinkageKind.EXTERNAL        = LinkageKind(4)


def _cursor_get_num_arguments(self):
    '''Call clang_Cursor_getNumArguments().'''
    return _cindex.conf.lib.clang_Cursor_getNumArguments(self)


def _cursor_linkage_kind(self):
    '''Call clang_getCursorLinkage().'''
    return LinkageKind(_cindex.conf.lib.clang_getCursorLinkage(self))


Cursor.get_num_arguments = _cursor_get_num_arguments
Cursor.linkage_kind = property(_cursor_linkage_kind)
