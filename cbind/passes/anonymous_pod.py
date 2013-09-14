# Copyright (C) 2013 Che-Liang Chiou.

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
    if tree.kind == CursorKind.TYPEDEF_DECL:
        _typedef_pod(tree)
    elif tree.is_user_defined_pod_decl():
        _real_anonymous_pod(tree)


def _typedef_pod(tree):
    '''Handle typedef'ed anonymous PODs.'''
    type_ = tree.underlying_typedef_type
    if type_.kind not in (TypeKind.UNEXPOSED, TypeKind.RECORD):
        return
    decl = type_.get_declaration()
    # Check decl.spelling instead of decl.name here because we want
    # to find anonymous POD, which could already have a given name by
    # the _real_anonymous_pod() function.
    if decl.spelling:
        return
    decl.annotate(annotations.ORIGINAL_NAME, tree.original_name)
    tree.annotate(annotations.REQUIRED, False)


def _real_anonymous_pod(tree):
    '''Generate the name for the POD.'''
    if tree.original_name:
        return
    if tree.kind == CursorKind.STRUCT_DECL:
        kind = 'struct'
    elif tree.kind == CursorKind.CLASS_DECL:
        kind = 'class'
    else:
        kind = 'union'
    # I can't think of any test cases or real world scenarios
    # that tree.location.file is None...
    assert tree.location.file
    filename = re.sub(r'[^\w]', '_', tree.location.file.name)
    name = '_%s_%s_%d_%d' % (kind, filename,
            tree.location.line, tree.location.column)
    tree.annotate(annotations.ORIGINAL_NAME, name)
