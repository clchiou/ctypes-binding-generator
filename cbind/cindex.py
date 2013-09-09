# Copyright (C) 2013 Che-Liang Chiou.

'''Import either min_cindex or clang_cindex.'''

import pycbind


if pycbind.choose_cindex_impl() == pycbind.MIN_CINDEX:
    from cbind.min_cindex import (Index, Cursor, CursorKind,
            Type, TypeKind, LinkageKind)
else:
    from cbind.clang_cindex import (Index, Cursor, CursorKind,
            Type, TypeKind, LinkageKind)


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind', 'LinkageKind']
