'''Scan typedef of anonymous PODs.'''

from clang.cindex import CursorKind, TypeKind
from cbind.passes.util import traverse_postorder
import cbind.annotations as annotations


def scan_typedef_pod(syntax_tree):
    '''Scan typedef of anonymous PODs.'''
    traverse_postorder(syntax_tree, _scan_tree)


def _scan_tree(tree):
    '''Scan typedef of anonymous PODs.'''
    if tree.kind is not CursorKind.TYPEDEF_DECL:
        return
    type_ = tree.underlying_typedef_type
    if type_.kind not in (TypeKind.UNEXPOSED, TypeKind.RECORD):
        return
    decl = type_.get_declaration()
    if decl.spelling:
        return
    decl.annotate(annotations.NAME, tree.spelling)
    tree.annotate(annotations.REQUIRED, False)
