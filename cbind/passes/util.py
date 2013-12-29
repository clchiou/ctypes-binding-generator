# Copyright (C) 2013 Che-Liang Chiou.

'''Utility functions.'''

from cbind.cindex import CursorKind, TypeKind


def traverse_postorder(syntax_tree, postorder):
    '''Traverse syntax tree post order.'''
    prune = lambda tree: tree.kind == CursorKind.COMPOUND_STMT
    syntax_tree.traverse(postorder=postorder, prune=prune)


def strip_type(type_):
    '''Strip type one level.'''
    stripped_type = None
    if type_.kind == TypeKind.TYPEDEF:
        stripped_type = type_.get_canonical()
    elif type_.kind == TypeKind.CONSTANTARRAY:
        stripped_type = type_.get_array_element_type()
    elif type_.kind == TypeKind.POINTER:
        stripped_type = type_.get_pointee()
    return stripped_type
