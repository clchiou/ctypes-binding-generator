'''Minimum implementation that is compitable with clang.cindex.'''

# pylint: disable=C0103,W0108,W0142

from cbind._clang_index import Cursor, CursorKind, Type, TypeKind, LinkageKind
from cbind.min_cindex_helper import Index


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind', 'LinkageKind']
