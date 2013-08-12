'''Minimum implementation that is compitable with clang.cindex.'''

# pylint: disable=C0103,W0108,W0142

import collections
import re
from ctypes import CFUNCTYPE, byref, c_char_p, c_uint, c_void_p
import cbind._clang_index as _index


### Utilities


def make_method(funcptr):
    '''Make a (unbound) method from ctypes._FuncPtr object.'''
    # XXX This trampoline is necessary because ctypes._FuncPtr does not
    # implement Python descriptor, providing instance binding...
    return lambda self, *args: funcptr(self, *args)


# TODO(clchiou): cached_property produces strange bugs.  I should fix it
# someday.  But make it an alias of property for now.

#class cached_property(object):  # pylint: disable=R0903
#    '''Cached property decorator.'''
#
#    def __init__(self, getter):
#        self.getter = getter
#        self.cache = {}
#
#    def __get__(self, object_, _):
#        if object_ is None:
#            return self
#        if self.cache.get(id(object_)) is None:
#            self.cache[id(object_)] = self.getter(object_)
#        return self.cache[id(object_)]

cached_property = property

### Register errcheck callbacks


def call_clang_getCString(result, *_):
    '''Call clang_getCString().'''
    return _index.clang_getCString(result)


_index.clang_getCursorSpelling.errcheck = call_clang_getCString
_index.clang_getFileName.errcheck = call_clang_getCString
_index.clang_getDiagnosticSpelling.errcheck = call_clang_getCString


def ref_translation_unit(result, _, arguments):
    '''Store a reference to TranslationUnit in the Python object so that
    it is not GC'ed before this cursor.'''
    # pylint: disable=W0212
    tunit = None
    for arg in arguments:
        if isinstance(arg, TranslationUnit):
            tunit = arg
            break
        if hasattr(arg, '_translation_unit'):
            tunit = arg._translation_unit
            break
    assert tunit is not None
    result._translation_unit = tunit
    return result


def check_cursor(result, function, arguments):
    '''Check returned cursor object.'''
    if result == _index.clang_getNullCursor():
        return None
    return ref_translation_unit(result, function, arguments)


_index.clang_Cursor_getArgument.errcheck = check_cursor
_index.clang_getTranslationUnitCursor.errcheck = check_cursor
_index.clang_getTypeDeclaration.errcheck = check_cursor


_index.clang_getArgType.errcheck = ref_translation_unit
_index.clang_getArrayElementType.errcheck = ref_translation_unit
_index.clang_getCanonicalType.errcheck = ref_translation_unit
_index.clang_getCursorType.errcheck = ref_translation_unit
_index.clang_getEnumDeclIntegerType.errcheck = ref_translation_unit
_index.clang_getPointeeType.errcheck = ref_translation_unit
_index.clang_getResultType.errcheck = ref_translation_unit
_index.clang_getTypedefDeclUnderlyingType.errcheck = ref_translation_unit


### Helper classes


class ClangObject(object):  # pylint: disable=R0903
    '''Helper for Clang objects.'''

    def __init__(self, object_):
        '''Initialize the object.'''
        if isinstance(object_, int):
            object_ = c_void_p(object_)
        self.object_ = self._as_parameter_ = object_


class File(ClangObject):  # pylint: disable=R0903
    '''File object.'''

    name = property(_index.clang_getFileName)


class DiagnosticsIterator(collections.Sequence):  # pylint: disable=R0903,R0924
    '''Indexable iterator object of diagnostics.'''

    def __init__(self, tunit):
        '''Initialize the object.'''
        self.tunit = tunit

    def __len__(self):
        return int(_index.clang_getNumDiagnostics(self.tunit))

    def __getitem__(self, index):
        diag = _index.clang_getDiagnostic(self.tunit, index)
        if not diag:
            raise IndexError()
        return Diagnostic(diag)


class Diagnostic(ClangObject):  # pylint: disable=R0903
    '''A diagnostic object.'''

    Ignored = 0
    Note    = 1
    Warning = 2
    Error   = 3
    Fatal   = 4

    def __del__(self):
        '''Delete the object.'''
        _index.clang_disposeDiagnostic(self)

    severity = property(_index.clang_getDiagnosticSeverity)
    location = property(_index.clang_getDiagnosticLocation)
    spelling = property(_index.clang_getDiagnosticSpelling)


class Index(ClangObject):
    '''Primary interface to Clang CIndex library.'''

    @staticmethod
    def create(excludeDecls=False):
        '''Create a new Index.'''
        return Index(_index.clang_createIndex(excludeDecls, 0))

    def __del__(self):
        '''Delete the object.'''
        _index.clang_disposeIndex(self)

    def parse(self, path, args=None, unsaved_files=None, options=0):
        '''Call TranslationUnit.from_source.'''
        return TranslationUnit.from_source(path, args, unsaved_files, options,
                self)


class TranslationUnitLoadError(Exception):
    '''Exception raised by TranslationUnit.'''
    pass


class TranslationUnit(ClangObject):
    '''Represent a source code translation unit.'''

    # pylint: disable=R0903,R0913

    @classmethod
    def from_source(cls, filename, args=None, unsaved_files=None, options=0,
            index=None):
        '''Create translation unit.'''
        args = args or []
        unsaved_files = unsaved_files or []
        index = index or Index.create()
        if args:
            args_array = (c_char_p * len(args))(*args)
        else:
            args_array = None
        if unsaved_files:
            unsaved_array = (_index.CXUnsavedFile * len(unsaved_files))()
            for i, (name, contents) in enumerate(unsaved_files):
                if hasattr(contents, 'read'):
                    contents = contents.read()
                unsaved_array[i].Filename = name
                unsaved_array[i].Contents = contents
                unsaved_array[i].Length = len(contents)
        else:
            unsaved_array = None
        ptr = _index.clang_parseTranslationUnit(index, filename,
                args_array, len(args),
                unsaved_array, len(unsaved_files),
                options)
        if not ptr:
            raise TranslationUnitLoadError('Error parsing translation unit.')
        return cls(ptr)

    def __del__(self):
        '''Delete the object.'''
        _index.clang_disposeTranslationUnit(self)

    cursor = property(_index.clang_getTranslationUnitCursor)
    diagnostics = property(DiagnosticsIterator)


### Patch methods to classes


_index.CXString.__del__ = make_method(_index.clang_disposeString)


def SourceLocation_data(self):
    '''Create SourceLocation data.'''
    file_, line, column, offset = c_void_p(), c_uint(), c_uint(), c_uint()
    _index.clang_getInstantiationLocation(self,
            byref(file_), byref(line), byref(column), byref(offset))
    if file_:
        file_ = File(file_)
    else:
        file_ = None
    return SourceLocationData(file_, line.value, column.value, offset.value)


SourceLocation = _index.CXSourceLocation
SourceLocation.__eq__ = lambda self, other: \
        _index.clang_equalLocations(self, other)
SourceLocation.__ne__ = lambda self, other: not self.__eq__(other)
SourceLocationData = collections.namedtuple('SourceLocationData',
        'file line column offset')
SourceLocation.data = cached_property(SourceLocation_data)
SourceLocation.file = property(lambda self: self.data.file)
SourceLocation.line = property(lambda self: self.data.line)
SourceLocation.column = property(lambda self: self.data.column)
SourceLocation.offset = property(lambda self: self.data.offset)


def Cursor_get_arguments(self):
    '''Return an iterator of arguments.'''
    num_args = _index.clang_Cursor_getNumArguments(self)
    for i in xrange(num_args):
        yield _index.clang_Cursor_getArgument(self, i)


def Cursor_get_children(self):
    '''Return a list of children.'''
    children = []
    def visit(child, *_):
        '''Visit children callback.'''
        assert child != _index.clang_getNullCursor()
        # Store reference to TranslationUnit...
        # pylint: disable=W0212
        child._translation_unit = self._translation_unit
        children.append(child)
        return 1  # continue
    callback_proto = CFUNCTYPE(_index.CXChildVisitResult,
            _index.CXCursor, _index.CXCursor, c_void_p)
    visit_callback = callback_proto(visit)
    _index.clang_visitChildren(self, visit_callback, None)
    return children


def Cursor_enum_value(self):
    '''Return the value of an enum constant.'''
    # pylint: disable=E1101
    underlying_type = self.type
    if underlying_type.kind == TypeKind.ENUM:
        underlying_type = underlying_type.get_declaration().enum_type
    if underlying_type.kind in (TypeKind.CHAR_U,
                                TypeKind.UCHAR,
                                TypeKind.CHAR16,
                                TypeKind.CHAR32,
                                TypeKind.USHORT,
                                TypeKind.UINT,
                                TypeKind.ULONG,
                                TypeKind.ULONGLONG,
                                TypeKind.UINT128):
        return _index.clang_getEnumConstantDeclUnsignedValue(self)
    else:
        return _index.clang_getEnumConstantDeclValue(self)


def Cursor_spelling(self):
    '''Return Cursor spelling.'''
    if not _index.clang_isDeclaration(self.kind):
        return None
    return _index.clang_getCursorSpelling(self)


Cursor = _index.CXCursor
Cursor.__eq__ = lambda self, other: _index.clang_equalCursors(self, other)
Cursor.__ne__ = lambda self, other: not self.__eq__(other)
Cursor.enum_type = cached_property(_index.clang_getEnumDeclIntegerType)
Cursor.enum_value = cached_property(Cursor_enum_value)
Cursor.get_arguments = Cursor_get_arguments
Cursor.get_bitfield_width = make_method(_index.clang_getFieldDeclBitWidth)
Cursor.get_children = Cursor_get_children
Cursor.get_num_arguments = make_method(_index.clang_Cursor_getNumArguments)
Cursor.is_bitfield = make_method(_index.clang_Cursor_isBitField)
Cursor.is_definition = make_method(_index.clang_isCursorDefinition)
Cursor.linkage_kind = property(lambda self: _index.clang_getCursorLinkage(self))
Cursor.location = cached_property(_index.clang_getCursorLocation)
Cursor.result_type = cached_property(
        lambda self: _index.clang_getResultType(self.type))
Cursor.spelling = cached_property(Cursor_spelling)
Cursor.type = cached_property(_index.clang_getCursorType)
Cursor.underlying_typedef_type = cached_property(
        _index.clang_getTypedefDeclUnderlyingType)


class ArgumentsIterator(collections.Sequence):  # pylint: disable=R0924
    '''Indexable iterator of arguments.'''

    def __init__(self, type_):
        '''Initialize the object.'''
        self.type_ = type_
        self.length = None

    def __len__(self):
        if self.length is None:
            self.length = _index.clang_getNumArgTypes(self.type_)
        return self.length

    def __getitem__(self, index):
        if not (0 <= index < len(self)):
            raise IndexError('Index out of range: index=%d, len=%d' %
                    (index, len(self)))
        result = _index.clang_getArgType(self.type_, index)
        if result.kind == TypeKind.INVALID:  # pylint: disable=E1101
            raise IndexError('Argument could not be retrieved.')
        return result


Type = _index.CXType
Type. __eq__ = lambda self, other: _index.clang_equalTypes(self, other)
Type.__ne__ = lambda self, other: not self.__eq__(other)
Type.argument_types = lambda self: ArgumentsIterator(self)
Type.get_align = make_method(_index.clang_Type_getAlignOf)
Type.get_array_element_type = make_method(_index.clang_getArrayElementType)
Type.get_array_size = make_method(_index.clang_getArraySize)
Type.get_canonical = make_method(_index.clang_getCanonicalType)
Type.get_declaration = make_method(_index.clang_getTypeDeclaration)
Type.get_pointee = make_method(_index.clang_getPointeeType)
Type.get_result = make_method(_index.clang_getResultType)
Type.is_function_variadic = make_method(_index.clang_isFunctionTypeVariadic)


### Add enum tables


def add_enum_constants(cls, name_matcher, converter):
    '''Add enum constants to class.'''
    cls_name = cls.__name__
    name_mapping = {}
    for name in dir(_index):
        match = name_matcher.match(name)
        if match:
            new_name = converter(match.group(1))
            value = getattr(_index, name)
            setattr(cls, new_name, cls(value))
            name_mapping[value] = new_name
    def to_str(self):
        '''Convert enum value to its name.'''
        return '%s.%s' % (cls_name, name_mapping[self.value])
    cls.__str__ = to_str


def camel_case_to_underscore(name):
    '''Convert CamelCase to CAMEL_CASE.'''
    return re.sub(r'([a-z])([A-Z])', r'\1_\2', name).upper()


CursorKind = _index.CXCursorKind
CursorKind.__hash__ = lambda self: int(self.value)
CursorKind.__eq__ = lambda self, other: self.value == other.value
CursorKind.__ne__ = lambda self, other: not self.__eq__(other)
add_enum_constants(CursorKind, re.compile(r'CXCursor_([\w_]+)'),
        camel_case_to_underscore)


TypeKind = _index.CXTypeKind
TypeKind.__hash__ = lambda self: int(self.value)
TypeKind.__eq__ = lambda self, other: self.value == other.value
TypeKind.__ne__ = lambda self, other: not self.__eq__(other)
add_enum_constants(TypeKind, re.compile(r'CXType_([\w_]+)'), str.upper)


LinkageKind = _index.CXLinkageKind
LinkageKind.__hash__ = lambda self: int(self.value)
LinkageKind.__eq__ = lambda self, other: self.value == other.value
LinkageKind.__ne__ = lambda self, other: not self.__eq__(other)
add_enum_constants(LinkageKind, re.compile(r'CXLinkage_([\w_]+)'),
        camel_case_to_underscore)
