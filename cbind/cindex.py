'''Import either min_cindex or clang_cindex.'''

try:
    from cbind.min_cindex import (Index, Cursor, CursorKind,
            Type, TypeKind, LinkageKind)
except ImportError:
    from cbind.clang_cindex import (Index, Cursor, CursorKind,
            Type, TypeKind, LinkageKind)


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind', 'LinkageKind']
