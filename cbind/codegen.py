# Copyright (C) 2013 Che-Liang Chiou.

'''Generate ctypes binding from syntax tree.'''

import logging
from cbind.cindex import CursorKind, TypeKind
import cbind.annotations as annotations


# Map of clang type to ctypes type
C_TYPE_MAP = {
        TypeKind.INVALID:           None,
        TypeKind.UNEXPOSED:         None,
        TypeKind.VOID:              None,
        TypeKind.BOOL:              'c_bool',
        TypeKind.CHAR_U:            'c_ubyte',
        TypeKind.UCHAR:             'c_ubyte',
        TypeKind.CHAR16:            None,
        TypeKind.CHAR32:            None,
        TypeKind.USHORT:            'c_ushort',
        TypeKind.UINT:              'c_uint',
        TypeKind.ULONG:             'c_ulong',
        TypeKind.ULONGLONG:         'c_ulonglong',
        TypeKind.UINT128:           None,
        TypeKind.CHAR_S:            'c_char',
        TypeKind.SCHAR:             'c_char',
        TypeKind.WCHAR:             'c_wchar',
        TypeKind.SHORT:             'c_short',
        TypeKind.INT:               'c_int',
        TypeKind.LONG:              'c_long',
        TypeKind.LONGLONG:          'c_longlong',
        TypeKind.INT128:            None,
        TypeKind.FLOAT:             'c_float',
        TypeKind.DOUBLE:            'c_double',
        TypeKind.LONGDOUBLE:        'c_longdouble',
        TypeKind.NULLPTR:           None,
        TypeKind.OVERLOAD:          None,
        TypeKind.DEPENDENT:         None,
        TypeKind.OBJCID:            None,
        TypeKind.OBJCCLASS:         None,
        TypeKind.OBJCSEL:           None,
        TypeKind.COMPLEX:           None,
        TypeKind.POINTER:           None,
        TypeKind.BLOCKPOINTER:      None,
        TypeKind.LVALUEREFERENCE:   None,
        TypeKind.RVALUEREFERENCE:   None,
        TypeKind.RECORD:            None,
        TypeKind.ENUM:              None,
        TypeKind.TYPEDEF:           None,
        TypeKind.OBJCINTERFACE:     None,
        TypeKind.OBJCOBJECTPOINTER: None,
        TypeKind.FUNCTIONNOPROTO:   None,
        TypeKind.FUNCTIONPROTO:     None,
        TypeKind.CONSTANTARRAY:     None,
        TypeKind.INCOMPLETEARRAY:   None,
        TypeKind.VARIABLEARRAY:     None,
        TypeKind.DEPENDENTSIZEDARRAY: None,
        TypeKind.VECTOR:            None,
}

# Typedef'ed types of stddef.h, etc.
BUILTIN_TYPEDEFS = {
        'size_t': 'c_size_t',
        'ssize_t': 'c_ssize_t',
        'wchar_t': 'c_wchar_t',
}

# Indent by 4 speces
INDENT = '    '

# Name of the library
LIBNAME = '_lib'


def gen_tree_node(tree, output):
    '''Generate ctypes binding from a AST node.'''
    if not tree.get_annotation(annotations.REQUIRED, False):
        return
    # Do not define a node twice.
    if tree.get_annotation(annotations.DEFINED, False):
        return
    declaration = False
    if tree.kind == CursorKind.TYPEDEF_DECL:
        _make_typedef(tree, output)
    elif tree.kind == CursorKind.FUNCTION_DECL:
        _make_function(tree, output)
    elif (tree.kind == CursorKind.STRUCT_DECL or
            tree.kind == CursorKind.UNION_DECL):
        declared = tree.get_annotation(annotations.DECLARED, False)
        declaration = not tree.is_definition()
        gen_record(tree, output,
                declared=declared, declaration=declaration)
    elif tree.kind == CursorKind.ENUM_DECL and tree.is_definition():
        _make_enum(tree, output)
    elif tree.kind == CursorKind.VAR_DECL:
        _make_var(tree, output)
    else:
        return
    output.write('\n')
    if declaration:
        tree.annotate(annotations.DECLARED, True)
    else:
        tree.annotate(annotations.DEFINED, True)


def gen_record(tree, output, declared=False, declaration=False):
    '''Generate ctypes binding of a POD definition.'''
    if not declared:
        _make_pod_header(tree, tree.name, output)
    if not declaration:
        _make_pod_body(tree, tree.name, output)


def _make_type(type_):
    '''Generate ctypes binding of a clang type.'''
    c_type = None
    if type_.is_user_defined_type():
        tree = type_.get_declaration()
        c_type = tree.name
        if not c_type and tree.kind == CursorKind.ENUM_DECL:
            c_type = _make_type(tree.enum_type)
    elif type_.kind == TypeKind.TYPEDEF:
        tree = type_.get_declaration()
        c_type = (BUILTIN_TYPEDEFS.get(tree.name) or
                _make_type(type_.get_canonical()))
    elif type_.kind == TypeKind.CONSTANTARRAY:
        # TODO(clchiou): Make parentheses context-sensitive
        element_type = _make_type(type_.get_array_element_type())
        c_type = '(%s * %d)' % (element_type, type_.get_array_size())
    elif type_.kind == TypeKind.INCOMPLETEARRAY:
        pointee_type = type_.get_array_element_type()
        c_type = _make_pointer_type(pointee_type=pointee_type)
    elif type_.kind == TypeKind.POINTER:
        c_type = _make_pointer_type(pointer_type=type_)
    else:
        c_type = C_TYPE_MAP.get(type_.kind)
    if c_type is None:
        raise TypeError('Unsupported TypeKind: %s' % type_.kind)
    return c_type


def _make_pointer_type(pointer_type=None, pointee_type=None):
    '''Generate ctypes binding of a pointer.'''
    if pointer_type:
        pointee_type = pointer_type.get_pointee()
    canonical = pointee_type.get_canonical()
    decl = pointee_type.get_declaration()
    if pointee_type.kind == TypeKind.CHAR_S:
        c_type = 'c_char_p'
    elif pointee_type.kind == TypeKind.WCHAR:
        c_type = 'c_wchar_p'
    elif pointee_type.kind == TypeKind.VOID:
        c_type = 'c_void_p'
    elif (pointee_type.kind == TypeKind.TYPEDEF and
            canonical.kind == TypeKind.VOID):
        # Handle special case "typedef void foo;"
        c_type = 'c_void_p'
    elif (pointee_type.kind == TypeKind.TYPEDEF and decl.name == 'wchar_t'):
        c_type = 'c_wchar_p'
    elif canonical.kind == TypeKind.FUNCTIONPROTO:
        c_type = _make_function_pointer(canonical)
    else:
        c_type = 'POINTER(%s)' % _make_type(pointee_type)
    return c_type


def _make_function_pointer(type_):
    '''Generate ctypes binding of a function pointer.'''
    # ctypes does not support variadic function pointer...
    if type_.is_function_variadic():
        logging.info('Could not generate pointer to variadic function')
        return 'c_void_p'
    args = type_.get_argument_types()
    if len(args) > 0:
        argtypes = ', %s' % ', '.join(_make_type(arg) for arg in args)
    else:
        argtypes = ''
    result_type = type_.get_result()
    if result_type.kind == TypeKind.VOID:
        restype = 'None'
    else:
        restype = _make_type(result_type)
    return 'CFUNCTYPE(%s%s)' % (restype, argtypes)


def _make_typedef(tree, output):
    '''Generate ctypes binding of a typedef statement.'''
    type_ = tree.underlying_typedef_type
    # Handle special case "typedef void foo;"
    if type_.kind == TypeKind.VOID:
        return
    output.write('%s = %s\n' % (tree.name, _make_type(type_)))


def _make_function(tree, output):
    '''Generate ctypes binding of a function declaration.'''
    if not tree.is_external_linkage():
        return
    output.write('{0} = {1}.{2}\n'.format(tree.name, LIBNAME, tree.spelling))
    argtypes = ', '.join(make_function_argtypes(tree))
    if argtypes:
        output.write('%s.argtypes = [%s]\n' % (tree.name, argtypes))
    if tree.result_type.kind != TypeKind.VOID:
        restype = make_function_restype(tree)
        output.write('%s.restype = %s\n' % (tree.name, restype))
    errcheck = tree.get_annotation(annotations.ERRCHECK, False)
    if errcheck:
        output.write('%s.errcheck = %s\n' % (tree.name, errcheck))
    method = tree.get_annotation(annotations.METHOD, False)
    if method:
        output.write('%s = _CtypesFunctor(%s)\n' % (method, tree.name))


def make_function_argtypes(tree):
    '''Generate ctypes binding of function's arguments.'''
    if tree.type.is_function_variadic() or tree.get_num_arguments() <= 0:
        return ()
    return tuple(_make_type(arg.type) for arg in tree.get_arguments())


def make_function_restype(tree):
    '''Make function restype.'''
    if tree.result_type.kind == TypeKind.VOID:
        return 'None'
    return _make_type(tree.result_type)


def _make_pod_header(tree, name, output):
    '''Generate the 'class ...' part of POD.'''
    if tree.kind == CursorKind.STRUCT_DECL:
        pod_kind = 'Structure'
    else:
        pod_kind = 'Union'
    mixin = tree.get_annotation(annotations.MIXIN, ())
    if mixin:
        fmt = 'class {name}({mixin}, {kind}):\n{indent}pass\n'
    else:
        fmt = 'class {name}({kind}):\n{indent}pass\n'
    output.write(fmt.format(name=name, kind=pod_kind, indent=INDENT,
        mixin=', '.join(mixin)))


def _make_pod_body(tree, name, output):
    '''Generate the body part of POD.'''
    fields = tuple(tree.get_field_declaration())
    if not fields:
        return
    begin = '%s.' % name
    field_stmt = '%s_fields_ = [' % begin
    indent = ' ' * len(field_stmt)
    output.write(field_stmt)
    first = True
    for field in fields:
        blob = ['\'%s\'' % field.name, _make_type(field.type)]
        if field.is_bitfield():
            blob.append(str(field.get_bitfield_width()))
        field_stmt = '(%s)' % ', '.join(blob)
        if first:
            first = False
        else:
            output.write(',\n%s' % indent)
        output.write('%s' % field_stmt)
    output.write(']\n')


def _make_enum(tree, output):
    '''Generate ctypes binding of a enum definition.'''
    if tree.name:
        enum_name = tree.name
        enum_type = _make_type(tree.enum_type)
    else:
        enum_name = ''
        enum_type = 'c_uint'
    if tree.name:
        mixin = tree.get_annotation(annotations.MIXIN, ())
        if mixin:
            fmt = 'class {name}({mixin}, {type}):\n{indent}pass\n'
        else:
            fmt = 'class {name}({type}):\n{indent}pass\n'
        output.write(fmt.format(name=enum_name, indent=INDENT,
            type=enum_type, mixin=', '.join(mixin)))
    for enum in tree.get_children():
        if not enum.get_annotation(annotations.REQUIRED, False):
            continue
        fmt = enum.get_annotation(annotations.ENUM,
                '{enum_field} = {enum_value}')
        output.write(fmt.format(enum_name=enum_name, enum_type=enum_type,
            enum_field=enum.name, enum_value=enum.enum_value))
        output.write('\n')


def _make_var(tree, output):
    '''Generate ctypes binding of a variable declaration.'''
    c_type = _make_type(tree.type)
    output.write('{0} = {1}.in_dll({2}, \'{3}\')\n'.
            format(tree.name, c_type, LIBNAME, tree.spelling))
