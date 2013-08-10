'''Import either min_cindex or clang_cindex.'''

try:
    from cbind.min_cindex import (Index, Cursor, CursorKind, Type, TypeKind,
        clang_getCursorLinkage, clang_Cursor_getNumArguments)
except ImportError:
    from cbind.clang_cindex import (Index, Cursor, CursorKind, Type, TypeKind,
        clang_getCursorLinkage, clang_Cursor_getNumArguments)


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind',
        'clang_getCursorLinkage', 'clang_Cursor_getNumArguments']
