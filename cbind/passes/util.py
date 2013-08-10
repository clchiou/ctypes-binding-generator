'''Utility functions.'''

from cbind.cindex import CursorKind, TypeKind


def traverse_postorder(syntax_tree, postorder):
    '''Traverse syntax tree post order.'''
    syntax_tree.traverse(postorder=postorder,
            prune=lambda tree: tree.kind is CursorKind.COMPOUND_STMT)


def strip_type(type_):
    '''Strip type one level.'''
    stripped_type = None
    if type_.kind is TypeKind.TYPEDEF:
        stripped_type = type_.get_canonical()
    elif type_.kind is TypeKind.CONSTANTARRAY:
        stripped_type = type_.get_array_element_type()
    elif type_.kind is TypeKind.POINTER:
        stripped_type = type_.get_pointee()
    return stripped_type
