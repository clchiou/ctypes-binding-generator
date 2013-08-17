'''Scan syntax tree and rename nodes.'''

from cbind.passes.util import traverse_postorder
import cbind.annotations as annotations


def scan_and_rename(syntax_tree, rename_rules):
    '''Scan syntax tree and rename nodes.'''
    if not rename_rules:
        return

    def _rename(tree):
        '''Rename nodes.'''
        if not tree.name:
            return
        for pattern, rewrite in rename_rules:
            new_name = pattern.sub(rewrite, tree.name)
            if new_name != tree.name:
                tree.annotate(annotations.NAME, new_name)
                break

    traverse_postorder(syntax_tree, _rename)
