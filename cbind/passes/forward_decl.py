'''Scan syntax tree for forward declarations.'''

from cbind.cindex import CursorKind
from cbind.passes.util import traverse_postorder, strip_type
import cbind.annotations as annotations


def scan_forward_decl(syntax_tree):
    '''Scan syntax tree for forward declarations.'''
    has_seen = set()
    traverse_postorder(syntax_tree, lambda tree: _scan_tree(tree, has_seen))


def _scan_tree(tree, has_seen):
    '''Scan tree for forward declarations.'''
    if tree.is_user_defined_type_decl():
        has_seen.add(tree)

    if tree.kind == CursorKind.FUNCTION_DECL:
        for type_ in tree.type.get_argument_types():
            _scan_type_forward_decl(type_, has_seen)
        _scan_type_forward_decl(tree.result_type, has_seen)
    else:
        _scan_type_forward_decl(tree.type, has_seen)


def _scan_type_forward_decl(type_, has_seen):
    '''Scan type for forward declarations.'''
    if type_.is_user_defined_type():
        tree = type_.get_declaration()
        if tree.is_user_defined_type_decl() and tree not in has_seen:
            tree.annotate(annotations.FORWARD_DECLARATION, True)
        return

    stripped_type = strip_type(type_)
    if stripped_type:
        _scan_type_forward_decl(stripped_type, has_seen)
