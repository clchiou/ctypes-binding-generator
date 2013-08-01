'''Data structures representing C source codes'''

from collections import defaultdict
from ctypes import c_uint
from clang.cindex import Index, Cursor
from clang.cindex import conf, register_function


def _hash_cursor(cursor):
    '''Compute the hash-key of the cursor.'''
    if cursor.spelling:
        return '%s:%s' % (cursor.kind, cursor.spelling)
    if cursor.location.file:
        filename = cursor.location.file.name
    else:
        filename = '?'
    return '%s:%s:%d' % (cursor.kind, filename, cursor.location.offset)

# XXX: Patch libclang.Cursor class
Cursor.__hash__ = _hash_cursor


# clang Index.h enum CXLinkageKind
CXLINKAGE_INVALID = 0
CXLINKAGE_NOLINKAGE = 1
CXLINKAGE_INTERNAL = 2
CXLINKAGE_UNIQUEEXTERNAL = 3
CXLINKAGE_EXTERNAL = 4

# Register libclang function.
register_function(conf.lib, ('clang_getCursorLinkage', [Cursor], c_uint), False)


class SyntaxTree:
    '''Class represents an abstract syntax tree.'''

    PROPERTIES = frozenset('''
        enum_type
        enum_value
        is_definition
        kind
        location
        result_type
        spelling
        type
        underlying_typedef_type
    '''.split())

    _index = Index.create()

    @classmethod
    def parse(cls, path, contents=None, args=None):
        '''Parse C source file.'''
        if contents:
            unsaved_files = [(path, contents)]
        else:
            unsaved_files = None
        tunit = cls._index.parse(path, args=args, unsaved_files=unsaved_files)
        if not tunit:
            message = 'Could not parse C source: %s' % path
            raise ValueError(message)
        return cls(tunit.cursor)

    def __init__(self, cursor, annotation_table=None):
        '''Initialize the object.'''
        self.cursor = cursor
        self.annotation_table = annotation_table or defaultdict(dict)

    def __getattr__(self, name):
        if name not in self.PROPERTIES:
            message = "'SyntaxTree' object has no attribute '%s'" % name
            raise AttributeError(message)
        return getattr(self.cursor, name)

    def is_external_linkage(self):
        '''Test if linkage is external.'''
        linkage_kind = conf.lib.clang_getCursorLinkage(self.cursor)
        return linkage_kind == CXLINKAGE_EXTERNAL

    def get_arguments(self):
        '''Get arguments.'''
        for arg_cursor in self.cursor.get_arguments():
            yield SyntaxTree(arg_cursor, self.annotation_table)

    def get_children(self):
        '''Get sub-trees.'''
        for child_cursor in self.cursor.get_children():
            yield SyntaxTree(child_cursor, self.annotation_table)

    def traverse(self, preorder=None, postorder=None, prune=None):
        '''Traverse the syntax tree.'''
        if prune and prune(self):
            return
        if preorder:
            preorder(self)
        for child_tree in self.get_children():
            child_tree.traverse(preorder, postorder, prune)
        if postorder:
            postorder(self)

    def annotate(self, key, value):
        '''Annotate this node.'''
        annotations = self.annotation_table.get(self.cursor)
        annotations[key] = value

    def get_annotation(self, key, default=None):
        '''Get the annotation.'''
        annotations = self.annotation_table.get(self.cursor)
        if default is None:
            return annotations[key]
        else:
            return annotations.get(key, default)
