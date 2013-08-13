'''Import either min_cindex or clang_cindex.'''

import cbind


if cbind.cindex_choice() == cbind.MIN_CINDEX:
    from cbind.min_cindex import (Index, Cursor, CursorKind,
            Type, TypeKind, LinkageKind)
else:
    from cbind.clang_cindex import (Index, Cursor, CursorKind,
            Type, TypeKind, LinkageKind)


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind', 'LinkageKind']
