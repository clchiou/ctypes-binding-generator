# Copyright (C) 2013 Che-Liang Chiou.

'''Data structures representing C source codes'''

from collections import defaultdict
from os.path import basename
import logging

import cbind.annotations as annotations
from cbind.cindex import (Index, Cursor, CursorKind, Diagnostic,
                          Type, TypeKind, LinkageKind)


class SyntaxTreeForest(list):
    '''A list of syntax trees that share a common annotation table.'''

    def __init__(self):
        '''Initialize the object.'''
        self.annotation_table = defaultdict(dict)
        super(SyntaxTreeForest, self).__init__()

    def parse(self, path, contents=None, args=None):
        '''Parse C source file.'''
        syntax_tree = SyntaxTree.parse(path, contents=contents, args=args,
                                       annotation_table=self.annotation_table)
        self.append(syntax_tree)
        return syntax_tree


def _make_subtree_iterator(iter_cursors):
    '''Create wrapper of cursor iterator.'''
    def wrapper(self):
        '''Wrapper of cursor iterator.'''
        for cursor in iter_cursors(self.cursor):
            yield SyntaxTree(cursor, None, self.annotation_table)
    return wrapper


class SyntaxTree:
    '''Class represents an abstract syntax tree.'''

    SEVERITY = Diagnostic.Warning

    PROPERTIES = frozenset('''
        enum_type
        enum_value
        get_bitfield_width
        get_num_arguments
        is_bitfield
        is_definition
        is_static_method
        kind
        location
        result_type
        semantic_parent
        spelling
        type
        underlying_typedef_type
    '''.split())

    UDT_DECL = frozenset((CursorKind.STRUCT_DECL,
                          CursorKind.CLASS_DECL,
                          CursorKind.UNION_DECL,
                          CursorKind.ENUM_DECL))

    POD_DECL = frozenset((CursorKind.STRUCT_DECL,
                          CursorKind.CLASS_DECL,
                          CursorKind.UNION_DECL))

    UDT_FIELD_DECL = frozenset((CursorKind.ENUM_CONSTANT_DECL,
                                CursorKind.FIELD_DECL))

    HAS_FIELD_DECL = frozenset((CursorKind.STRUCT_DECL,
                                CursorKind.CLASS_DECL,
                                CursorKind.UNION_DECL))

    HAS_METHOD_DECL = frozenset((CursorKind.STRUCT_DECL,
                                 CursorKind.CLASS_DECL))

    @classmethod
    def parse(cls, path, contents=None, args=None, annotation_table=None):
        '''Parse C source file.'''
        if contents:
            unsaved_files = [(path, contents)]
        else:
            unsaved_files = None
        # XXX Hold Index object at local level instead of module level
        # because Python module cleanup does not guarantee that this module
        # is cleaned up before cbind.cindex (and libclang).  If the cleanup
        # ordering is reversed, Index.__del__ will be called after libclang
        # is released.
        index = Index.create()
        tunit = index.parse(path, args=args, unsaved_files=unsaved_files)
        for diag in tunit.diagnostics:
            # I can't think of any test cases or real world scenarios
            # that diag.location.file is None...
            assert diag.location.file
            severity_str = {
                Diagnostic.Ignored: 'IGNORE',
                Diagnostic.Note:    'NOTE',
                Diagnostic.Warning: 'WARNING',
                Diagnostic.Error:   'ERROR',
                Diagnostic.Fatal:   'FATAL',
            }[diag.severity]
            message = '%s:%d:%d: %s: %s' % (diag.location.file.name,
                                            diag.location.line,
                                            diag.location.column,
                                            severity_str,
                                            diag.spelling)
            if diag.severity >= cls.SEVERITY:
                raise SyntaxError(message)
            logging.info(message)
        if annotation_table is None:
            annotation_table = defaultdict(dict)
        return cls(tunit.cursor, tunit, annotation_table)

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
            filename = basename(cursor.location.file.name)
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
        if isinstance(attr, Cursor):
            attr = SyntaxTree(attr, None, self.annotation_table)
        elif isinstance(attr, Type):
            attr = SyntaxTreeType(attr, self)
        return attr

    @property
    def original_name(self):
        '''Return original_name of this node.'''
        return self.get_annotation(annotations.ORIGINAL_NAME, self.spelling)

    @property
    def name(self):
        '''Return name of this node.'''
        return self.get_annotation(annotations.NAME, self.original_name)

    def is_external_linkage(self):
        '''Test if linkage is external.'''
        return self.cursor.linkage_kind == LinkageKind.EXTERNAL

    def is_user_defined_type_decl(self):
        '''Test if this node is declaration of user-defined type.'''
        return self.kind in self.UDT_DECL

    def is_user_defined_pod_decl(self):
        '''Test if this node is declaration of user-defined POD type.'''
        return self.kind in self.POD_DECL

    def is_field_decl(self):
        '''Test if this is a field declaration.'''
        return self.kind in self.UDT_FIELD_DECL

    get_children = _make_subtree_iterator(Cursor.get_children)
    get_arguments = _make_subtree_iterator(Cursor.get_arguments)

    def get_field_declaration(self):
        '''Get direct sub-trees that are field declaration.'''
        if self.kind not in self.HAS_FIELD_DECL:
            return
        for child_tree in self.get_children():
            if child_tree.kind == CursorKind.FIELD_DECL:
                yield child_tree

    def get_method(self):
        '''Get member methods of a class.'''
        if self.kind not in self.HAS_METHOD_DECL:
            return
        for child_tree in self.get_children():
            if child_tree.kind == CursorKind.CXX_METHOD:
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

    def get_annotation(self, key, default):
        '''Get the annotation.'''
        return self.annotation_table[self].get(key, default)


def _make_type_getter(getter):
    '''Create wrapper of type getter.'''
    def wrapper(self):
        '''Wrapper of type getter.'''
        c_type = getter(self.c_type)
        return SyntaxTreeType(c_type, self.syntax_tree)
    return wrapper


class SyntaxTreeType:
    '''Class represents C type.'''

    PROPERTIES = frozenset('''
        is_const_qualified
        is_function_variadic
        is_volatile_qualified
        get_align
        get_array_size
        get_offset
        get_ref_qualifier
        kind
    '''.split())

    # User-defined types
    UDT = frozenset((TypeKind.UNEXPOSED, TypeKind.RECORD, TypeKind.ENUM))

    def __init__(self, c_type, syntax_tree):
        '''Initialize the object.'''
        self.c_type = c_type
        self.syntax_tree = syntax_tree

    def __eq__(self, _):
        '''Wrapper of __eq__().'''
        raise AttributeError('__eq__ not implemented')

    def __ne__(self, other):
        '''Implement __ne__().'''
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

    get_array_element_type = _make_type_getter(Type.get_array_element_type)
    get_canonical = _make_type_getter(Type.get_canonical)
    get_class_type = _make_type_getter(Type.get_class_type)
    if hasattr(Type, 'element_type'):
        get_element_type = _make_type_getter(lambda c_type:
                                             c_type.element_type)
    else:
        get_element_type = _make_type_getter(Type.get_element_type)
    get_pointee = _make_type_getter(Type.get_pointee)
    get_result = _make_type_getter(Type.get_result)

    def get_argument_types(self):
        '''Get type of arguments.'''
        return tuple(SyntaxTreeType(c_type, self.syntax_tree)
                     for c_type in self.c_type.argument_types())

    def is_user_defined_type(self):
        '''Test if this type is user-defined.'''
        return self.kind in self.UDT
