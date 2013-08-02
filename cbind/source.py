'''Data structures representing C source codes'''

from collections import defaultdict
from ctypes import c_uint

import clang.cindex as cindex
from clang.cindex import CursorKind, TypeKind


# clang Index.h enum CXLinkageKind
CXLINKAGE_INVALID = 0
CXLINKAGE_NOLINKAGE = 1
CXLINKAGE_INTERNAL = 2
CXLINKAGE_UNIQUEEXTERNAL = 3
CXLINKAGE_EXTERNAL = 4

# Register libclang function.
cindex.register_function(cindex.conf.lib,
        ('clang_getCursorLinkage', [cindex.Cursor], c_uint), False)


def _make_subtree_iterator(iter_cursors):
    '''Create wrapper of cursor iterator.'''
    def wrapper(self):
        '''Wrapper of cursor iterator.'''
        for cursor in iter_cursors(self.cursor):
            yield SyntaxTree(cursor, None, self.annotation_table)
    return wrapper


class SyntaxTree:
    '''Class represents an abstract syntax tree.'''

    PROPERTIES = frozenset('''
        enum_type
        enum_value
        get_bitfield_width
        is_bitfield
        is_definition
        kind
        location
        result_type
        spelling
        type
        underlying_typedef_type
    '''.split())

    UDT_DECL = frozenset((CursorKind.STRUCT_DECL,
        CursorKind.UNION_DECL,
        CursorKind.ENUM_DECL))

    HAS_FIELD_DECL = frozenset((CursorKind.STRUCT_DECL, CursorKind.UNION_DECL))

    _index = cindex.Index.create()

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
        return cls(tunit.cursor, tunit, defaultdict(dict))

    def __init__(self, cursor, translation_unit, annotation_table):
        '''Initialize the object.'''
        self.cursor = cursor
        self.translation_unit = translation_unit
        self.annotation_table = annotation_table

    def __eq__(self, other):
        '''Implement __eq__().'''
        return hash(self) == hash(other)

    def __ne__(self, other):
        '''Implement __ne__().'''
        return not self.__eq__(other)

    def __hash__(self):
        '''Compute hash of the cursor.'''
        cursor = self.cursor
        if cursor.spelling:
            return hash('%s:%s' % (cursor.kind, cursor.spelling))
        if cursor.location.file:
            filename = cursor.location.file.name
        else:
            filename = '?'
        return hash('%s:%s:%d' %
                (cursor.kind, filename, cursor.location.offset))

    def __getattr__(self, name):
        '''Get property.'''
        if name not in self.PROPERTIES:
            cls = self.__class__.__name__
            message = '\'%s\' object has no attribute \'%s\'' % (cls, name)
            raise AttributeError(message)
        attr = getattr(self.cursor, name)
        if isinstance(attr, cindex.Type):
            # Wrap cindex.Type instance
            attr = Type(attr, self)
        return attr

    def is_external_linkage(self):
        '''Test if linkage is external.'''
        linkage_kind = cindex.conf.lib.clang_getCursorLinkage(self.cursor)
        return linkage_kind == CXLINKAGE_EXTERNAL

    def is_user_defined_type_decl(self):
        '''Test if this node is declaration of user-defined type.'''
        return self.kind in self.UDT_DECL

    @property
    def num_arguments(self):
        '''Get number of arguments.'''
        return cindex.conf.lib.clang_Cursor_getNumArguments(self.cursor)

    get_children = _make_subtree_iterator(cindex.Cursor.get_children)
    get_arguments = _make_subtree_iterator(cindex.Cursor.get_arguments)

    def get_field_declaration(self):
        '''Get direct sub-trees that are field declaration.'''
        if self.kind not in self.HAS_FIELD_DECL:
            return
        for child_tree in self.get_children():
            if child_tree.kind is CursorKind.FIELD_DECL:
                yield child_tree

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
        self.annotation_table[self][key] = value

    def get_annotation(self, key, default=None):
        '''Get the annotation.'''
        annotations = self.annotation_table[self]
        if default is None:
            return annotations[key]
        else:
            return annotations.get(key, default)


def _make_type_getter(getter):
    '''Create wrapper of type getter.'''
    def wrapper(self):
        '''Wrapper of type getter.'''
        c_type = getter(self.c_type)
        return Type(c_type, self.syntax_tree)
    return wrapper


class Type:
    '''Class represents C type.'''

    PROPERTIES = frozenset('''
        is_function_variadic
        get_align
        get_array_size
        kind
    '''.split())

    # User-defined types
    UDT = frozenset((TypeKind.UNEXPOSED, TypeKind.RECORD, TypeKind.ENUM))

    def __init__(self, c_type, syntax_tree):
        '''Initialize the object.'''
        self.c_type = c_type
        self.syntax_tree = syntax_tree

    def __eq__(self, other):
        '''Wrapper of __eq__().'''
        return self.c_type == other.c_type

    def __ne__(self, other):
        '''Wrapper of __ne__().'''
        return not self.__eq__(other)

    def __getattr__(self, name):
        '''Get property.'''
        if name not in self.PROPERTIES:
            cls = self.__class__.__name__
            message = '\'%s\' object has no attribute \'%s\'' % (cls, name)
            raise AttributeError(message)
        attr = getattr(self.c_type, name)
        return attr

    def get_declaration(self):
        '''Wrapper of get_declaration.'''
        cursor = self.c_type.get_declaration()
        return SyntaxTree(cursor, None, self.syntax_tree.annotation_table)

    get_array_element_type = \
            _make_type_getter(cindex.Type.get_array_element_type)
    get_canonical = _make_type_getter(cindex.Type.get_canonical)
    get_pointee = _make_type_getter(cindex.Type.get_pointee)
    get_result = _make_type_getter(cindex.Type.get_result)

    def get_argument_types(self):
        '''Get type of arguments.'''
        return tuple(Type(c_type, self.syntax_tree)
                for c_type in self.c_type.argument_types())

    def is_user_defined_type(self):
        '''Test if this type is user-defined.'''
        return self.kind in self.UDT
