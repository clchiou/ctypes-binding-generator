'''Minimum implementation that is compitable with clang.cindex.'''

# pylint: disable=C0103,W0108,W0142

import collections
import re
from ctypes import CFUNCTYPE, byref, c_char_p, c_uint, c_void_p
import cbind._clang_index as _index


### Utilities


class cursor_cached_property(object):  # pylint: disable=R0903
    '''Cached property decorator for Cursor class.'''

    def __init__(self, getter):
        self.getter = getter
        self.cache = {}

    def __get__(self, cursor, _):
        if cursor is None:
            return self
        key = _index.clang_hashCursor(cursor)
        if key not in self.cache:
            self.cache[key] = self.getter(cursor)
        return self.cache[key]


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
            unsaved_array = (_index.UnsavedFile * len(unsaved_files))()
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


def SourceLocation_data(self):
    '''Create SourceLocation data.'''
    # pylint: disable=W0212
    if not hasattr(self, '_data'):
        file_, line, column, offset = c_void_p(), c_uint(), c_uint(), c_uint()
        _index.clang_getInstantiationLocation(self,
                byref(file_), byref(line), byref(column), byref(offset))
        if file_:
            file_ = File(file_)
        else:
            file_ = None
        self._data = SourceLocationData(file_,
                line.value, column.value, offset.value)
    return self._data


SourceLocation = _index.SourceLocation
SourceLocation.__eq__ = lambda self, other: \
        _index.clang_equalLocations(self, other)
SourceLocation.__ne__ = lambda self, other: not self.__eq__(other)
SourceLocationData = collections.namedtuple('SourceLocationData',
        'file line column offset')
SourceLocation.data = property(SourceLocation_data)
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
    callback_proto = CFUNCTYPE(_index.ChildVisitResult,
            _index.Cursor, _index.Cursor, c_void_p)
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


Cursor = _index.Cursor
Cursor.__eq__ = lambda self, other: _index.clang_equalCursors(self, other)
Cursor.__ne__ = lambda self, other: not self.__eq__(other)
Cursor.enum_type = cursor_cached_property(_index.clang_getEnumDeclIntegerType)
Cursor.enum_value = cursor_cached_property(Cursor_enum_value)
Cursor.get_arguments = Cursor_get_arguments
Cursor.get_children = Cursor_get_children
Cursor.linkage_kind = property(lambda self: _index.clang_getCursorLinkage(self))
Cursor.location = cursor_cached_property(_index.clang_getCursorLocation)
Cursor.result_type = cursor_cached_property(
        lambda self: _index.clang_getResultType(self.type))
Cursor.semantic_parent = \
        cursor_cached_property(_index.clang_getCursorSemanticParent)
Cursor.spelling = cursor_cached_property(Cursor_spelling)
Cursor.type = cursor_cached_property(_index.clang_getCursorType)
Cursor.underlying_typedef_type = cursor_cached_property(
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


Type = _index.Type
Type. __eq__ = lambda self, other: _index.clang_equalTypes(self, other)
Type.__ne__ = lambda self, other: not self.__eq__(other)
Type.argument_types = lambda self: ArgumentsIterator(self)


### Add enum tables


def add_enum_constants(cls, name_matcher, converter):
    '''Add enum constants to class.'''
    cls_name = cls.__name__
    name_mapping = {}
    for name, value in vars(_index).iteritems():
        match = name_matcher.match(name)
        if match:
            new_name = converter(match.group(1))
            setattr(cls, new_name, cls(value))
            name_mapping[value] = new_name
    def to_str(self):
        '''Convert enum value to its name.'''
        return '%s.%s' % (cls_name, name_mapping[self.value])
    cls.__str__ = to_str


def camel_case_to_underscore(name):
    '''Convert CamelCase to CAMEL_CASE.'''
    return re.sub(r'([a-z])([A-Z])', r'\1_\2', name).upper()


CursorKind = _index.CursorKind
CursorKind.__hash__ = lambda self: int(self.value)
CursorKind.__eq__ = lambda self, other: self.value == other.value
CursorKind.__ne__ = lambda self, other: not self.__eq__(other)
add_enum_constants(CursorKind, re.compile(r'Cursor_([\w_]+)'),
        camel_case_to_underscore)


TypeKind = _index.TypeKind
TypeKind.__hash__ = lambda self: int(self.value)
TypeKind.__eq__ = lambda self, other: self.value == other.value
TypeKind.__ne__ = lambda self, other: not self.__eq__(other)
add_enum_constants(TypeKind, re.compile(r'Type_([\w_]+)'), str.upper)


LinkageKind = _index.LinkageKind
LinkageKind.__hash__ = lambda self: int(self.value)
LinkageKind.__eq__ = lambda self, other: self.value == other.value
LinkageKind.__ne__ = lambda self, other: not self.__eq__(other)
add_enum_constants(LinkageKind, re.compile(r'Linkage_([\w_]+)'),
        camel_case_to_underscore)
