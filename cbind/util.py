'''Utility functions.'''


def walk_astree(cursor, preorder=None, postorder=None, prune=None):
    '''Recursively walk through the AST.'''
    if prune and prune(cursor):
        return
    if preorder:
        preorder(cursor)
    for child in cursor.get_children():
        walk_astree(child, preorder, postorder, prune)
    if postorder:
        postorder(cursor)
