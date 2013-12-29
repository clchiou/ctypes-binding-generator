# Copyright (C) 2013 Che-Liang Chiou.

'''Scan syntax tree for required nodes.'''

from cbind.cindex import CursorKind, TypeKind
from cbind.passes.util import traverse_postorder, strip_type
import cbind.annotations as annotations


def scan_required_nodes(syntax_tree, check_required):
    '''Breadth-first scan for required symbols.'''

    def _scan_required(tree):
        '''Mark nodes as required.'''
        if not check_required(tree):
            return
        tree.annotate(annotations.REQUIRED, True)
        _scan_type_definition(tree.type, todo, visited)
        if tree.is_field_decl():
            _scan_type_definition(tree.semantic_parent.type, todo, visited)
        elif tree.kind == CursorKind.FUNCTION_DECL:
            if (not tree.type.is_function_variadic() and
                    tree.get_num_arguments() > 0):
                for arg in tree.get_arguments():
                    _scan_type_definition(arg.type, todo, visited)
            if tree.result_type.kind != TypeKind.VOID:
                _scan_type_definition(tree.result_type, todo, visited)

    visited = set()
    todo = []
    traverse_postorder(syntax_tree, _scan_required)
    call_scan_type_definition = lambda tree: \
        _scan_type_definition(tree.type, todo, visited)
    while todo:
        # Trick is to copy todo and then empty it without creating a new list.
        trees = list(todo)
        todo[:] = []
        for tree in trees:
            tree.annotate(annotations.REQUIRED, True)
            traverse_postorder(tree, call_scan_type_definition)


def _scan_type_definition(type_, todo, visited):
    '''Scan type definition.'''
    if type_.is_user_defined_type():
        tree = type_.get_declaration()
        if not tree.is_user_defined_type_decl():
            return
        if tree in visited:
            return
        todo.append(tree)
        visited.add(tree)
        for field in tree.get_field_declaration():
            _scan_type_definition(field.type, todo, visited)
        return

    stripped_type = strip_type(type_)
    if stripped_type:
        _scan_type_definition(stripped_type, todo, visited)
