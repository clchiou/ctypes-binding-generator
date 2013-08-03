'''Scan syntax tree's use of __va_list_tag.'''

from clang.cindex import CursorKind
from cbind.passes.util import strip_type


def scan_va_list_tag(syntax_tree):
    '''Scan use of __va_list_tag.'''
    try:
        syntax_tree.traverse(
                postorder=lambda tree: _scan_tree(tree, syntax_tree),
                prune=lambda tree: tree.kind is CursorKind.COMPOUND_STMT)
    except StopIteration:
        pass


def _scan_tree(tree, root):
    '''Scan this tree for __va_list_tag.'''
    if not tree.get_annotation('required', False):
        return
    type_ = tree.type
    while True:
        if tree.spelling == '__va_list_tag':
            root.annotate('use_va_list_tag', tree)
            raise StopIteration()  # Return from deeply recursion
        while True:
            type_ = strip_type(type_)
            if not type_:
                return
            if type_.is_user_defined_type():
                tree = type_.get_declaration()
                break
