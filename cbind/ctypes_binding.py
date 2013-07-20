'''Parse and generate ctypes binding from C sources with clang.'''

import logging
from ctypes import c_uint
from clang.cindex import Index, Cursor, CursorKind, TypeKind
from clang.cindex import conf, register_function


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
        TypeKind.VECTOR:            None,
}

# Indent by 4 speces
INDENT = '    '

POD_DECL = frozenset((CursorKind.STRUCT_DECL, CursorKind.UNION_DECL))

BLOB_TYPE = frozenset((TypeKind.UNEXPOSED, TypeKind.RECORD))

CXLinkage_Invalid = 0
CXLinkage_NoLinkage = 1
CXLinkage_Internal = 2
CXLinkage_UniqueExternal = 3
CXLinkage_External = 4


# Register libclang function.
register_function(conf.lib,
        ('clang_getCursorLinkage', [Cursor], c_uint), False)


class CtypesBindingException(Exception):
    '''Exception raised by CtypesBindingGenerator class.'''
    pass


class CParser:
    '''Parse C source files with libclang.'''

    def __init__(self):
        '''Initialize the object.'''
        self._index = Index.create()
        self.symbol_table = SymbolTable()
        self.forward_declaration = SymbolTable()
        self.translation_units = []

    def parse(self, path, contents, args):
        '''Parse C source file.'''
        if contents:
            unsaved_files = [(path, contents)]
        else:
            unsaved_files = None
        translation_unit = self._index.parse(path, args=args,
                unsaved_files=unsaved_files)
        if not translation_unit:
            msg = 'Could not parse C source: %s' % path
            raise CtypesBindingException(msg)
        self.translation_units.append(translation_unit)
        walk_astree(translation_unit.cursor,
                postorder=self._extract_symbol, prune=self._prune_node)
        # Breadth-first scan for needed symbols.
        visited = SymbolTable()
        todo = []
        mark_needed = lambda cursor: self._mark_needed(cursor, todo, visited)
        for cursor in translation_unit.cursor.get_children():
            if not cursor.location.file or cursor.location.file.name != path:
                continue
            walk_astree(cursor, preorder=mark_needed)
        while todo:
            nodes = list(todo)
            todo[:] = [] # Clear todo but not create a new list.
            for cursor in nodes:
                walk_astree(cursor, preorder=mark_needed)

    def _not_mark_needed(self, cursor):
        '''Test if a cursor has not been marked as needed.'''
        return (cursor not in self.symbol_table or
                not self.symbol_table.get_annotation(cursor, 'needed', False))

    def _mark_needed(self, cursor, todo, visited):
        '''Mark node as needed.'''
        try:
            self.symbol_table.annotate(cursor, 'needed', True)
        except KeyError:
            pass
        self._scan_type(cursor.type, todo, visited)

    def _scan_type(self, type_, todo, visited):
        '''Scan type recursively for symbols.'''
        if type_.kind in BLOB_TYPE or type_.kind is TypeKind.ENUM:
            cursor = type_.get_declaration()
            if (cursor.kind not in POD_DECL and
                    cursor.kind is not CursorKind.ENUM_DECL):
                return
            if cursor in visited:
                return
            todo.append(cursor)
            visited.add(cursor)
            if cursor.kind in POD_DECL:
                for field in cursor.get_children():
                    if field.kind is CursorKind.FIELD_DECL:
                        self._scan_type(field.type, todo, visited)
        elif type_.kind is TypeKind.TYPEDEF:
            self._scan_type(type_.get_canonical(), todo, visited)
        elif type_.kind is TypeKind.CONSTANTARRAY:
            self._scan_type(type_.get_array_element_type(), todo, visited)
        elif type_.kind is TypeKind.POINTER:
            self._scan_type(type_.get_pointee(), todo, visited)

    def traverse(self, preorder, postorder):
        '''Traverse ASTs.'''
        for tunit in self.translation_units:
            walk_astree(tunit.cursor, preorder=preorder, postorder=postorder)

    @staticmethod
    def _prune_node(cursor):
        '''Prune nodes.'''
        if cursor.kind is CursorKind.COMPOUND_STMT:
            return True
        return False

    def _extract_symbol(self, cursor):
        '''Extract symbols that we should generate Python codes for.'''
        # Ignore this node if it does not belong to any C sources.
        if not cursor.location.file:
            return
        # Do not extract this node twice.
        if cursor in self.symbol_table:
            return

        # Add this node to the symbol table before searching for nodes that
        # this node depends on to avoid infinite recursion caused by cyclic
        # reference.
        if cursor.kind is CursorKind.TYPEDEF_DECL:
            self.symbol_table.add(cursor)
        elif cursor.kind is CursorKind.FUNCTION_DECL:
            self.symbol_table.add(cursor)
            for type_ in cursor.type.argument_types():
                self._extract_type(type_)
            self._extract_type(cursor.result_type)
        elif cursor.kind in POD_DECL and cursor.is_definition():
            self._extract_pod(cursor)
        elif cursor.kind is CursorKind.ENUM_DECL and cursor.is_definition():
            self.symbol_table.add(cursor)
        elif cursor.kind is CursorKind.VAR_DECL:
            self.symbol_table.add(cursor)
            self._extract_type(cursor.type)
        else:
            return

    def _extract_pod(self, cursor):
        '''Extract symbols from POD.'''
        for field in cursor.get_children():
            if field.kind is CursorKind.FIELD_DECL:
                self._extract_type(field.type)
            elif field.kind in POD_DECL:
                self._extract_symbol(field)
        self.symbol_table.add(cursor)

    def _extract_type(self, type_):
        '''Extract symbols from this clang type.'''
        if type_.kind in BLOB_TYPE:
            cursor = type_.get_declaration()
            if cursor.kind in POD_DECL and cursor not in self.symbol_table:
                self.forward_declaration.add(cursor)
        elif type_.kind is TypeKind.TYPEDEF:
            self._extract_type(type_.get_canonical())
        elif type_.kind is TypeKind.CONSTANTARRAY:
            self._extract_type(type_.get_array_element_type())
        elif type_.kind is TypeKind.POINTER:
            self._extract_type(type_.get_pointee())


class CtypesBindingGenerator:
    '''Generate ctypes binding from C source files with libclang.'''

    def __init__(self, libvar=None):
        '''Initialize the object.'''
        self.parser = CParser()
        self.libvar = libvar or '_lib'
        self.anonymous_serial = 0
        # For convenience...
        self.symbol_table = self.parser.symbol_table

    def parse(self, path, contents=None, args=None):
        '''Call parser.parse().'''
        self.parser.parse(path, contents, args)

    def generate(self, output):
        '''Generate ctypes binding.'''
        preorder = lambda cursor: self._make_forward_decl(cursor, output)
        postorder = lambda cursor: self._make(cursor, output)
        self.parser.traverse(preorder, postorder)

    def _ignore_node(self, cursor):
        '''Test if we can ignore this node.'''
        # Do not process node that is not in the symbol table.
        if cursor not in self.symbol_table:
            return True
        # Do not process node that is not needed
        if not self.symbol_table.get_annotation(cursor, 'needed', False):
            return True
        return False

    def _make_forward_decl(self, cursor, output):
        '''Generate forward declaration for nodes.'''
        if self._ignore_node(cursor):
            return
        if cursor not in self.parser.forward_declaration:
            return
        declared = self.symbol_table.get_annotation(cursor, 'declared', False)
        self._make_pod(cursor, output, declared=declared, declaration=True)
        self.symbol_table.annotate(cursor, 'declared', True)

    def _make(self, cursor, output):
        '''Generate ctypes binding from a AST node.'''
        if self._ignore_node(cursor):
            return
        # Do not define a node twice.
        if self.symbol_table.get_annotation(cursor, 'defined', False):
            return
        declaration = False
        if cursor.kind is CursorKind.TYPEDEF_DECL:
            self._make_typedef(cursor, output)
        elif cursor.kind is CursorKind.FUNCTION_DECL:
            self._make_function(cursor, output)
        elif cursor.kind in POD_DECL:
            declared = self.symbol_table.get_annotation(cursor,
                    'declared', False)
            declaration = not cursor.is_definition()
            self._make_pod(cursor, output,
                    declared=declared, declaration=declaration)
        elif cursor.kind is CursorKind.ENUM_DECL and cursor.is_definition():
            self._make_enum(cursor, output)
        elif cursor.kind is CursorKind.VAR_DECL:
            self._make_var(cursor, output)
        else:
            return
        output.write('\n')
        if declaration:
            self.symbol_table.annotate(cursor, 'declared', True)
        else:
            self.symbol_table.annotate(cursor, 'defined', True)

    def _make_type(self, type_):
        '''Generate ctypes binding of a clang type.'''
        c_type = None
        if type_.kind in BLOB_TYPE:
            cursor = type_.get_declaration()
            if cursor.spelling:
                c_type = cursor.spelling
            elif cursor.kind is CursorKind.ENUM_DECL:
                c_type = self._make_type(cursor.enum_type)
            else:
                c_type = self.symbol_table.get_annotation(cursor, 'name')
        elif type_.kind is TypeKind.TYPEDEF:
            c_type = self._make_type(type_.get_canonical())
        elif type_.kind is TypeKind.CONSTANTARRAY:
            # TODO(clchiou): Make parentheses context-sensitive
            element_type = self._make_type(type_.get_array_element_type())
            c_type = '(%s * %d)' % (element_type, type_.get_array_size())
        # TODO(clchiou): libclang does not expose IncompleteArray.
        #elif type_.kind is TypeKind.INCOMPLETEARRAY:
        #    pointee_type = type_.get_array_element_type()
        #    c_type = self._make_pointer_type(pointee_type=pointee_type)
        elif type_.kind is TypeKind.POINTER:
            c_type = self._make_pointer_type(pointer_type=type_)
        else:
            c_type = C_TYPE_MAP.get(type_.kind)
        if c_type is None:
            raise TypeError('Unsupported TypeKind: %s' % type_.kind)
        return c_type

    def _make_pointer_type(self, pointer_type=None, pointee_type=None):
        '''Generate ctypes binding of a pointer.'''
        if pointer_type:
            pointee_type = pointer_type.get_pointee()
        canonical = pointee_type.get_canonical()
        if pointee_type.kind is TypeKind.CHAR_S:
            return 'c_char_p'
        elif pointee_type.kind is TypeKind.WCHAR:
            return 'c_wchar_p'
        elif pointee_type.kind is TypeKind.VOID:
            return 'c_void_p'
        elif (pointee_type.kind is TypeKind.TYPEDEF and
                canonical.kind is TypeKind.VOID):
            # Handle special case "typedef void foo;"
            return 'c_void_p'
        elif canonical.kind is TypeKind.FUNCTIONPROTO:
            return self._make_function_pointer(canonical)
        else:
            return 'POINTER(%s)' % self._make_type(pointee_type)

    def _make_function_pointer(self, type_):
        '''Generate ctypes binding of a function pointer.'''
        # ctypes does not support variadic function pointer...
        if type_.is_function_variadic():
            logging.info('Could not generate pointer to variadic function')
            return 'c_void_p'
        args = type_.argument_types()
        if len(args) > 0:
            argtypes = ', %s' % ', '.join(self._make_type(arg) for arg in args)
        else:
            argtypes = ''
        result_type = type_.get_result()
        if result_type.kind is TypeKind.VOID:
            restype = 'None'
        else:
            restype = self._make_type(result_type)
        return 'CFUNCTYPE(%s%s)' % (restype, argtypes)

    def _make_typedef(self, cursor, output):
        '''Generate ctypes binding of a typedef statement.'''
        type_ = cursor.underlying_typedef_type
        # Handle special case "typedef void foo;"
        if type_.kind is TypeKind.VOID:
            return
        output.write('%s = %s\n' % (cursor.spelling, self._make_type(type_)))

    def _make_function(self, cursor, output):
        '''Generate ctypes binding of a function declaration.'''
        linkage_kind = conf.lib.clang_getCursorLinkage(cursor)
        if linkage_kind != CXLinkage_External:
            return
        name = cursor.spelling
        output.write('{0} = {1}.{0}\n'.format(name, self.libvar))
        argtypes = self._make_function_arguments(cursor)
        if argtypes:
            output.write('%s.argtypes = [%s]\n' % (name, argtypes))
        if cursor.result_type.kind is not TypeKind.VOID:
            restype = self._make_type(cursor.result_type)
            output.write('%s.restype = %s\n' % (name, restype))

    def _make_function_arguments(self, cursor):
        '''Generate ctypes binding of function's arguments.'''
        num_args = conf.lib.clang_Cursor_getNumArguments(cursor)
        if cursor.type.is_function_variadic() or num_args <= 0:
            return None
        args = (self._make_type(arg.type) for arg in cursor.get_arguments())
        return ', '.join(args)

    def _make_pod(self, cursor, output, declared=False, declaration=False):
        '''Generate ctypes binding of a POD definition.'''
        name = self._make_pod_name(cursor)
        output_header = not declared
        output_body = not declaration
        if output_header:
            self._make_pod_header(cursor, name, output_body, output)
        if output_body:
            self._make_pod_body(cursor, name, output_header, output)

    def _make_pod_name(self, cursor):
        '''Generate the name of the POD.'''
        if cursor.spelling:
            name = cursor.spelling
        else:
            if cursor.kind is CursorKind.STRUCT_DECL:
                name = '_anonymous_struct_%04d'
            else:
                name = '_anonymous_union_%04d'
            name = name % self._next_anonymous_serial()
            self.symbol_table.annotate(cursor, 'name', name)
        return name

    @staticmethod
    def _make_pod_header(cursor, name, output_body, output):
        '''Generate the 'class ...' part of POD.'''
        if cursor.kind is CursorKind.STRUCT_DECL:
            pod_kind = 'Structure'
        else:
            pod_kind = 'Union'
        output.write('class {0}({1}):\n'.format(name, pod_kind))
        if not output_body:
            output.write('%spass\n' % INDENT)

    def _make_pod_body(self, cursor, name, output_header, output):
        '''Generate the body part of POD.'''
        fields = [field for field in cursor.get_children()
                if field.kind is CursorKind.FIELD_DECL]
        if not fields:
            if output_header:
                output.write('%spass\n' % INDENT)
            return
        if output_header:
            begin = INDENT
        else:
            begin = '%s.' % name
        # Generate _anonymous_
        anonymous = []
        for field in fields:
            if self._is_pod_field_anonymous(field):
                anonymous.append('\'%s\'' % field.spelling)
        if len(anonymous) == 1:
            output.write('%s_anonymous_ = (%s,)\n' %
                    (begin, anonymous[0]))
        elif anonymous:
            output.write('%s_anonymous_ = (%s)\n' %
                    (begin, ', '.join(anonymous)))
        # Generate _pack_
        output.write('%s_pack_ = %d\n' %
                (begin, cursor.type.get_align()))
        # Generate _fields_
        self._make_pod_fields(begin, fields, output)

    def _make_pod_fields(self, begin, fields, output):
        '''Generate ctypes _field_ statement.'''
        field_stmt = '%s_fields_ = [' % begin
        indent = ' ' * len(field_stmt)
        output.write(field_stmt)
        first = True
        for field in fields:
            blob = ['\'%s\'' % field.spelling, self._make_type(field.type)]
            if field.is_bitfield():
                blob.append(str(field.get_bitfield_width()))
            field_stmt = '(%s)' % ', '.join(blob)
            if first:
                first = False
            else:
                output.write(',\n%s' % indent)
            output.write('%s' % field_stmt)
        output.write(']\n')

    @staticmethod
    def _is_pod_field_anonymous(field):
        '''Test if this field is an anonymous one.'''
        if field.type.kind is not TypeKind.UNEXPOSED:
            return False
        cursor = field.type.get_declaration()
        return not bool(cursor.spelling)

    def _make_enum(self, cursor, output):
        '''Generate ctypes binding of a enum definition.'''
        if cursor.spelling:
            output.write('%s = %s\n' %
                    (cursor.spelling, self._make_type(cursor.enum_type)))
            c_type = cursor.spelling
        else:
            c_type = self._make_type(cursor.enum_type)
        for enum in cursor.get_children():
            output.write('%s = %s(%s)\n' %
                    (enum.spelling, c_type, enum.enum_value))

    def _make_var(self, cursor, output):
        '''Generate ctypes binding of a variable declaration.'''
        name = cursor.spelling
        c_type = self._make_type(cursor.type)
        output.write('{0} = {1}.in_dll({2}, \'{0}\')\n'.
                format(name, c_type, self.libvar))

    def _next_anonymous_serial(self):
        '''Generate a serial number for anonymous stuff.'''
        self.anonymous_serial += 1
        return self.anonymous_serial


class SymbolTable:
    '''Table of AST nodes.  This table may store nodes as well as annotations
    of nodes; this feature is useful for recording the names generated for
    anonymous POD (struct or union).
    '''

    @staticmethod
    def _hash_node(node):
        '''Compute the hash-key of the node.'''
        if node.spelling:
            return '%s:%s' % (node.kind, node.spelling)
        if node.location.file:
            filename = node.location.file.name
        else:
            filename = '?'
        return '%s:%s:%d' % (node.kind, filename, node.location.offset)

    def __init__(self):
        '''Initialize an empty SymbolTable.'''
        self._table = {}

    def __contains__(self, node):
        '''Return true if node is in the table.'''
        node_key = self._hash_node(node)
        return node_key in self._table

    def add(self, node):
        '''Store node as a pair of the node and its annotations.'''
        node_key = self._hash_node(node)
        if node_key in self._table:
            return
        self._table[node_key] = (node, {})

    def annotate(self, node, key, value):
        '''Annotate a node with (key, value).'''
        node_key = self._hash_node(node)
        annotations = self._table[node_key][1]
        annotations[key] = value

    def get_annotation(self, node, key, default=None):
        '''Get the annotation value of key of the node.'''
        node_key = self._hash_node(node)
        annotations = self._table[node_key][1]
        if default is None:
            return annotations[key]
        else:
            return annotations.get(key, default)


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
