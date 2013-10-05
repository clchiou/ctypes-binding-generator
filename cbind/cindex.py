# Copyright (C) 2013 Che-Liang Chiou.

'''Import either min_cindex or clang_cindex.'''

import cbind


if cbind.choose_cindex_impl() == cbind.MIN_CINDEX:
    from cbind.min_cindex import (Index, Cursor, CursorKind, Diagnostic,
            Type, TypeKind, LinkageKind, RefQualifierKind)
else:
    from cbind.clang_cindex import (Index, Cursor, CursorKind, Diagnostic,
            Type, TypeKind, LinkageKind, RefQualifierKind)


__all__ = ['Index', 'Cursor', 'CursorKind', 'Diagnostic',
        'Type', 'TypeKind', 'LinkageKind', 'RefQualifierKind']
