'''Scan syntax tree for required nodes.'''

from clang.cindex import CursorKind
from cbind.passes.util import strip_type


def scan_required_nodes(syntax_tree, path):
    '''Breadth-first scan for required symbols.'''
    visited = set()
    todo = []
    syntax_tree.traverse(
            lambda tree: _check_locally_defined(tree, path, todo, visited),
            prune=lambda tree: tree.kind is CursorKind.COMPOUND_STMT)
    call_scan_type_definition = lambda tree: _scan_type_definition(tree.type,
            todo, visited)
    while todo:
        # Trick is to copy todo and then empty it without creating a new list.
        trees = list(todo)
        todo[:] = []
        for tree in trees:
            tree.annotate('required', True)
            tree.traverse(call_scan_type_definition,
                    prune=lambda tree: tree.kind is CursorKind.COMPOUND_STMT)


def _check_locally_defined(tree, path, todo, visited):
    '''Mark locally defined nodes.'''
    if not tree.location.file or tree.location.file.name != path:
        return
    tree.annotate('required', True)
    _scan_type_definition(tree.type, todo, visited)


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
