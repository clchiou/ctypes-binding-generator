# Copyright (C) 2013 Che-Liang Chiou.

'''Scan syntax tree and rename nodes.'''

from cbind.passes.util import traverse_postorder


def scan_and_rename(syntax_tree, rename):
    '''Scan syntax tree and rename nodes.'''
    traverse_postorder(syntax_tree, rename)
