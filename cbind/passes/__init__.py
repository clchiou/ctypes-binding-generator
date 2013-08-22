'''Package of syntax tree passes (transformations).'''

from cbind.passes.required_nodes import scan_required_nodes
from cbind.passes.rename import scan_and_rename
from cbind.passes.forward_decl import scan_forward_decl
from cbind.passes.va_list_tag import scan_va_list_tag
from cbind.passes.anonymous_pod import scan_anonymous_pod


def custom_pass(syntax_tree, func):
    '''Run a custom pass over the tree.'''
    from cbind.passes.util import traverse_postorder
    traverse_postorder(syntax_tree, func)
