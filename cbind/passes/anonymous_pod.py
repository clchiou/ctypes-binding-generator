'''Scan anonymous PODs.'''

import re
from cbind.cindex import CursorKind, TypeKind
from cbind.passes.util import traverse_postorder
import cbind.annotations as annotations


def scan_anonymous_pod(syntax_tree):
    '''Scan anonymous PODs.'''
    traverse_postorder(syntax_tree, _scan_tree)


def _scan_tree(tree):
    '''Scan anonymous PODs.'''
    if tree.kind is CursorKind.TYPEDEF_DECL:
        _typedef_pod(tree)
    elif (tree.kind is CursorKind.STRUCT_DECL or
            tree.kind is CursorKind.UNION_DECL):
        _real_anonymous_pod(tree)


def _typedef_pod(tree):
    '''Handle typedef'ed anonymous PODs.'''
    type_ = tree.underlying_typedef_type
    if type_.kind not in (TypeKind.UNEXPOSED, TypeKind.RECORD):
        return
    decl = type_.get_declaration()
    if decl.spelling:
        return
    decl.annotate(annotations.NAME, tree.spelling)
    tree.annotate(annotations.REQUIRED, False)


def _real_anonymous_pod(tree):
    '''Generate the name for the POD.'''
    if tree.spelling:
        return
    if tree.get_annotation(annotations.NAME, False):
        return
    if tree.kind is CursorKind.STRUCT_DECL:
        kind = 'struct'
    else:
        kind = 'union'
    if tree.location.file:
        filename = re.sub(r'[^\w]', '_', tree.location.file.name)
    else:
        filename = 'none'
    name = '_%s_%s_%d_%d' % (kind, filename,
            tree.location.line, tree.location.column)
    tree.annotate(annotations.NAME, name)
