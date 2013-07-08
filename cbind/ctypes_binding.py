'''Parse and generate ctypes binding from C sources with clang.'''

from clang.cindex import Index, CursorKind, TypeKind, conf


# Map of clang type to ctypes type
C_TYPE_MAP = {
        TypeKind.INVALID:           None,
        TypeKind.UNEXPOSED:         None,
        TypeKind.VOID:              None,
        TypeKind.BOOL:              'c_bool',
        TypeKind.CHAR_U:            'c_uchar',
        TypeKind.UCHAR:             'c_uchar',
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


class CtypesBindingException(Exception):
    '''Exception raised by CtypesBindingGenerator class.'''
    pass


class CtypesBindingGenerator:
    '''Generate ctypes binding from C source files with libclang.'''

    # Indent by 4 speces
    indent = '    '

    c_type_map = C_TYPE_MAP

    blob_type = frozenset((TypeKind.UNEXPOSED, TypeKind.RECORD))
    pod_decl = frozenset((CursorKind.STRUCT_DECL, CursorKind.UNION_DECL))

    def __init__(self, libvar=None):
        '''Initialize the object.'''
        self.index = Index.create()
        self.symbol_table = SymbolTable()
        self.translation_units = []
        self.anonymous_serial = 0
        self.libvar = libvar or '_lib'
        self._c_src = None
        self._output = None

    def _walk_astree(self, cursor, func):
        '''Recursively walk through the AST.'''
        for child in cursor.get_children():
            self._walk_astree(child, func)
        func(cursor)

    def parse(self, path, contents=None, args=None):
        '''Parse C source file.'''
        if contents:
            unsaved_files = [(path, contents)]
        else:
            unsaved_files = None
        translation_unit = self.index.parse(path, args=args,
                unsaved_files=unsaved_files)
        if not translation_unit:
            msg = 'Could not parse C source: %s' % path
            raise CtypesBindingException(msg)
        self.translation_units.append(translation_unit)

        # We run through the AST for two passes:
        # * The first pass (right below) enumerates the symbols that we should
        #   generate Python codes for.
        # * The second pass in the generate() method generates the codes.
        self._c_src = path
        self._walk_astree(translation_unit.cursor, self._extract_symbol)

    def _extract_symbol(self, cursor):
        '''Extract symbols that we should generate Python codes for.'''
        # Ignore this node if it does not belong to the C source.
        if (not cursor.location.file or
                cursor.location.file.name != self._c_src):
            return
        # Do not extract this node twice.
        if cursor in self.symbol_table:
            return
        self.symbol_table.add(cursor)

        # Search for nodes that this node depends on.
        if cursor.kind is CursorKind.FUNCTION_DECL:
            for type_ in cursor.type.argument_types():
                self._extract_type(type_)
            self._extract_type(cursor.result_type)
        elif cursor.kind in self.pod_decl and cursor.is_definition():
            for field in cursor.get_children():
                if field.kind is CursorKind.FIELD_DECL:
                    self._extract_type(field.type)
        elif cursor.kind is CursorKind.VAR_DECL:
            self._extract_type(cursor.type)

    def _extract_type(self, type_):
        '''Extract symbols from this clang type.'''
        if type_.kind in self.blob_type:
            self.symbol_table.add(type_.get_declaration())
        elif type_.kind is TypeKind.TYPEDEF:
            self._extract_type(type_.get_canonical())
        elif type_.kind is TypeKind.CONSTANTARRAY:
            self._extract_type(type_.get_array_element_type())
        elif type_.kind is TypeKind.POINTER:
            self._extract_type(type_.get_pointee())

    def generate(self, output):
        '''Generate ctypes binding.'''
        self._output = output
        for tunit in self.translation_units:
            self._walk_astree(tunit.cursor, self._generate)

    def _generate(self, cursor):
        '''Generate ctypes binding from a AST node.'''
        # Do not process node that is not in the symbol table.
        if cursor not in self.symbol_table:
            return
        # Do not process a node twice.
        if self.symbol_table.get_annotation(cursor, 'processed', False):
            return
        # TODO(clchiou): Function pointer.
        if cursor.kind is CursorKind.TYPEDEF_DECL:
            self._make_typedef(cursor, self._output)
        elif cursor.kind is CursorKind.FUNCTION_DECL:
            self._make_function(cursor, self._output)
        elif cursor.kind in self.pod_decl and cursor.is_definition():
            self._make_pod(cursor, self._output)
        elif cursor.kind is CursorKind.ENUM_DECL and cursor.is_definition():
            self._make_enum(cursor, self._output)
        elif cursor.kind is CursorKind.VAR_DECL:
            self._make_var(cursor, self._output)
        else:
            return
        self._output.write('\n')
        self.symbol_table.annotate(cursor, 'processed', True)

    def _make_type(self, type_):
        '''Generate ctypes binding of a clang type.'''
        c_type = None
        if type_.kind in self.blob_type:
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
            element_type = self._make_type(type_.get_array_element_type())
            c_type = '%s * %d' % (element_type, type_.get_array_size())
        elif type_.kind is TypeKind.POINTER:
            c_type = self._make_pointer_type(type_)
        else:
            c_type = self.c_type_map.get(type_.kind)
        if c_type is None:
            raise TypeError('Unsupported TypeKind: %s' % type_.kind)
        return c_type

    def _make_pointer_type(self, type_):
        '''Generate ctypes binding of a pointer.'''
        pointee_type = type_.get_pointee()
        if pointee_type.kind is TypeKind.CHAR_S:
            return 'c_char_p'
        elif pointee_type.kind is TypeKind.WCHAR:
            return 'c_wchar_p'
        elif pointee_type.kind is TypeKind.VOID:
            return 'c_void_p'
        else:
            return 'POINTER(%s)' % self._make_type(pointee_type)

    def _make_typedef(self, cursor, output):
        '''Generate ctypes binding of a typedef statement.'''
        typedef_type = self._make_type(cursor.underlying_typedef_type)
        output.write('%s = %s\n' % (cursor.spelling, typedef_type))

    def _make_function(self, cursor, output):
        '''Generate ctypes binding of a function declaration.'''
        name = cursor.spelling
        output.write('{0} = {1}.{0}\n'.format(name, self.libvar))
        if conf.lib.clang_Cursor_getNumArguments(cursor):
            argtypes = '[%s]' % ', '.join(self._make_type(type_)
                    for type_ in cursor.type.argument_types())
            output.write('%s.argtypes = %s\n' % (name, argtypes))
        if cursor.result_type.kind is not TypeKind.VOID:
            restype = self._make_type(cursor.result_type)
            output.write('%s.restype = %s\n' % (name, restype))

    def _make_pod(self, cursor, output):
        '''Generate ctypes binding of a POD definition.'''
        if cursor.spelling:
            name = cursor.spelling
        else:
            if cursor.kind is CursorKind.STRUCT_DECL:
                name = '_anonymous_struct_%04d'
            else:
                name = '_anonymous_union_%04d'
            name = name % self._next_anonymous_serial()
            self.symbol_table.annotate(cursor, 'name', name)
        if cursor.kind is CursorKind.STRUCT_DECL:
            pod_kind = 'Structure'
        else:
            pod_kind = 'Union'
        output.write('class {0}({1}):\n'.format(name, pod_kind))
        fields = [field for field in cursor.get_children()
                if field.kind is CursorKind.FIELD_DECL]
        if not fields:
            output.write('%spass\n' % self.indent)
            return
        # Generate _anonymous_
        anonymous = []
        for field in fields:
            if self._is_pod_field_anonymous(field):
                anonymous.append('\'%s\'' % field.spelling)
        if len(anonymous) == 1:
            output.write('%s_anonymous_ = (%s,)\n' %
                    (self.indent, anonymous[0]))
        elif anonymous:
            output.write('%s_anonymous_ = (%s)\n' %
                    (self.indent, ', '.join(anonymous)))
        # Generate _pack_
        output.write('%s_pack_ = %d\n' %
                (self.indent, cursor.type.get_align()))
        # Generate _fields_
        self._make_pod_fields(fields, output)

    def _make_pod_fields(self, fields, output):
        '''Generate ctypes _field_ statement.'''
        field_stmt = '%s_fields_ = [' % self.indent
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
