'''Scan syntax tree for forward declarations.'''

from clang.cindex import CursorKind
from cbind.passes.util import strip_type


def scan_forward_decl(syntax_tree):
    '''Scan syntax tree for forward declarations.'''
    has_seen = set()
    syntax_tree.traverse(postorder=lambda tree: _scan_tree(tree, has_seen),
            prune=lambda tree: tree.kind is CursorKind.COMPOUND_STMT)


def _scan_tree(tree, has_seen):
    '''Scan tree for forward declarations.'''
    if tree.is_user_defined_type_decl():
        has_seen.add(tree)

    if tree.kind is CursorKind.FUNCTION_DECL:
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
            tree.annotate('forward-declaration', True)
        return

    stripped_type = strip_type(type_)
    if stripped_type:
        _scan_type_forward_decl(stripped_type, has_seen)
