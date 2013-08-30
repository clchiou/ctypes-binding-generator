'''Helpers for _clang_index module.'''

from collections import Sequence, namedtuple
from ctypes import CFUNCTYPE, byref, c_uint, c_char_p, c_void_p

import cbind._clang_index


# pylint: disable=C0103,W0212,W0108,W0142


class ClangObject(object):  # pylint: disable=R0903
    '''Helper for Clang objects.'''

    def __init__(self, object_):
        '''Initialize the object.'''
        if isinstance(object_, int):
            object_ = c_void_p(object_)
        self.object_ = self._as_parameter_ = object_


class File(ClangObject):
    '''File object.'''

    # pylint: disable=R0903,C0111

    @property
    def name(self):
        return cbind._clang_index.clang_getFileName(self)


class DiagnosticsIterator(Sequence):  # pylint: disable=R0903,R0924
    '''Indexable iterator object of diagnostics.'''

    def __init__(self, tunit):
        '''Initialize the object.'''
        self.tunit = tunit

    def __len__(self):
        return int(cbind._clang_index.clang_getNumDiagnostics(self.tunit))

    def __getitem__(self, index):
        diag = cbind._clang_index.clang_getDiagnostic(self.tunit, index)
        if not diag:
            raise IndexError()
        return Diagnostic(diag)


class Diagnostic(ClangObject):
    '''A diagnostic object.'''

    # pylint: disable=R0903,C0111

    Ignored = 0
    Note    = 1
    Warning = 2
    Error   = 3
    Fatal   = 4

    def __del__(self):
        '''Delete the object.'''
        cbind._clang_index.clang_disposeDiagnostic(self)

    @property
    def severity(self):
        return cbind._clang_index.clang_getDiagnosticSeverity(self)

    @property
    def location(self):
        return cbind._clang_index.clang_getDiagnosticLocation(self)

    @property
    def spelling(self):
        return cbind._clang_index.clang_getDiagnosticSpelling(self)


class Index(ClangObject):
    '''Primary interface to Clang CIndex library.'''

    @staticmethod
    def create(excludeDecls=False):
        '''Create a new Index.'''
        return Index(cbind._clang_index.clang_createIndex(excludeDecls, 0))

    def __del__(self):
        '''Delete the object.'''
        cbind._clang_index.clang_disposeIndex(self)

    def parse(self, path, args=None, unsaved_files=None, options=0):
        '''Call TranslationUnit.from_source.'''
        return TranslationUnit.from_source(path, args, unsaved_files, options,
                self)


class TranslationUnitLoadError(Exception):
    '''Exception raised by TranslationUnit.'''
    pass


class TranslationUnit(ClangObject):
    '''Represent a source code translation unit.'''

    # pylint: disable=R0903,R0913,C0111

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
            unsaved_array = (cbind._clang_index.UnsavedFile *
                    len(unsaved_files))()
            for i, (name, contents) in enumerate(unsaved_files):
                if hasattr(contents, 'read'):
                    contents = contents.read()
                unsaved_array[i].Filename = name
                unsaved_array[i].Contents = contents
                unsaved_array[i].Length = len(contents)
        else:
            unsaved_array = None
        ptr = cbind._clang_index.clang_parseTranslationUnit(index, filename,
                args_array, len(args),
                unsaved_array, len(unsaved_files),
                options)
        if not ptr:
            raise TranslationUnitLoadError('Error parsing translation unit.')
        return cls(ptr)

    def __del__(self):
        '''Delete the object.'''
        cbind._clang_index.clang_disposeTranslationUnit(self)

    @property
    def cursor(self):
        return cbind._clang_index.clang_getTranslationUnitCursor(self)

    @property
    def diagnostics(self):
        return DiagnosticsIterator(self)


def ref_translation_unit(result, _, arguments):
    '''Store a reference to TranslationUnit in the Python object so that
    it is not GC'ed before this cursor.'''
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
    if result == cbind._clang_index.clang_getNullCursor():
        return None
    return ref_translation_unit(result, function, arguments)


class cached_property(object):  # pylint: disable=R0903
    '''Cached property decorator for Cursor class.'''

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, cursor, _):
        if cursor is None:
            return self
        value = self.getter(cursor)
        setattr(cursor, self.getter.__name__, value)
        return value


SourceLocationData = namedtuple('SourceLocationData',
        'file line column offset')


class SourceLocationMixin(object):
    '''Mixin class of SourceLocation.'''

    # pylint: disable=C0111

    def __eq__(self, other):
        return cbind._clang_index.clang_equalLocations(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def file(self):
        return self.data.file

    @property
    def line(self):
        return self.data.line

    @property
    def column(self):
        return self.data.column

    @property
    def offset(self):
        return self.data.offset

    @cached_property
    def data(self):
        file_, line, column, offset = c_void_p(), c_uint(), c_uint(), c_uint()
        cbind._clang_index.clang_getInstantiationLocation(self,
                byref(file_), byref(line), byref(column), byref(offset))
        if file_:
            file_ = File(file_)
        else:
            file_ = None
        return SourceLocationData(file_, line.value, column.value, offset.value)


class CursorMixin(object):
    '''Mixin class of Cursor.'''

    # pylint: disable=C0111

    def __eq__(self, other):
        return cbind._clang_index.clang_equalCursors(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    @cached_property
    def enum_type(self):
        return cbind._clang_index.clang_getEnumDeclIntegerType(self)

    @property
    def linkage_kind(self):
        return cbind._clang_index.clang_getCursorLinkage(self)

    @cached_property
    def location(self):
        return cbind._clang_index.clang_getCursorLocation(self)

    @cached_property
    def result_type(self):
        return cbind._clang_index.clang_getResultType(self.type)

    @cached_property
    def semantic_parent(self):
        return cbind._clang_index.clang_getCursorSemanticParent(self)

    @cached_property
    def type(self):
        return cbind._clang_index.clang_getCursorType(self)

    @cached_property
    def underlying_typedef_type(self):
        return cbind._clang_index.clang_getTypedefDeclUnderlyingType(self)

    @cached_property
    def enum_value(self):
        '''Return the value of an enum constant.'''
        # pylint: disable=E1101
        underlying_type = self.type
        if underlying_type.kind == cbind._clang_index.TypeKind.ENUM:
            underlying_type = underlying_type.get_declaration().enum_type
        if underlying_type.kind in (cbind._clang_index.TypeKind.CHAR_U,
                                    cbind._clang_index.TypeKind.UCHAR,
                                    cbind._clang_index.TypeKind.CHAR16,
                                    cbind._clang_index.TypeKind.CHAR32,
                                    cbind._clang_index.TypeKind.USHORT,
                                    cbind._clang_index.TypeKind.UINT,
                                    cbind._clang_index.TypeKind.ULONG,
                                    cbind._clang_index.TypeKind.ULONGLONG,
                                    cbind._clang_index.TypeKind.UINT128):
            return cbind._clang_index.\
                    clang_getEnumConstantDeclUnsignedValue(self)
        else:
            return cbind._clang_index.clang_getEnumConstantDeclValue(self)

    @cached_property
    def spelling(self):
        '''Return Cursor spelling.'''
        if not cbind._clang_index.clang_isDeclaration(self.kind):
            return None
        return cbind._clang_index.clang_getCursorSpelling(self)

    def get_arguments(self):
        '''Return an iterator of arguments.'''
        num_args = cbind._clang_index.clang_Cursor_getNumArguments(self)
        for i in xrange(num_args):
            yield cbind._clang_index.clang_Cursor_getArgument(self, i)

    def get_children(self):
        '''Return a list of children.'''
        children = []
        def visit(child, *_):
            '''Visit children callback.'''
            assert child != cbind._clang_index.clang_getNullCursor()
            # Store reference to TranslationUnit...
            child._translation_unit = self._translation_unit
            children.append(child)
            return 1  # continue
        callback_proto = CFUNCTYPE(cbind._clang_index.ChildVisitResult,
                cbind._clang_index.Cursor, cbind._clang_index.Cursor, c_void_p)
        visit_callback = callback_proto(visit)
        cbind._clang_index.clang_visitChildren(self, visit_callback, None)
        return children


class ArgumentsIterator(Sequence):
    '''Indexable iterator of arguments.'''

    # pylint: disable=R0903

    def __init__(self, type_):
        '''Initialize the object.'''
        self.type_ = type_
        self.length = None

    def __len__(self):
        if self.length is None:
            self.length = cbind._clang_index.clang_getNumArgTypes(self.type_)
        return self.length

    def __getitem__(self, index):
        if not (0 <= index < len(self)):
            raise IndexError('Index out of range: index=%d, len=%d' %
                    (index, len(self)))
        result = cbind._clang_index.clang_getArgType(self.type_, index)
        # pylint: disable=E1101
        if result.kind == cbind._clang_index.TypeKind.INVALID:
            raise IndexError('Argument could not be retrieved.')
        return result

    def __setitem__(self, *_):
        raise AttributeError('__setitem__ is not implemented')

    def __delitem__(self, *_):
        raise AttributeError('__delitem__ is not implemented')


class TypeMixin(object):
    '''Mixin class of Type.'''

    # pylint: disable=R0903

    def __eq__(self, other):
        return cbind._clang_index.clang_equalTypes(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def argument_types(self):
        '''Return argument types iterator.'''
        return ArgumentsIterator(self)


class EnumerateKindMixin(object):
    '''Mixin class of CursorKind, TypeKind, and LinkageKind.'''

    # pylint: disable=R0903

    @classmethod
    def register(cls, name, value):
        '''Register enum constant.'''
        if not hasattr(cls, 'enum_value_map'):
            cls.enum_value_map = {}
        cls.enum_value_map[value] = name
        setattr(cls, name, cls(value))

    def __hash__(self):
        return int(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '%s.%s' % (type(self).__name__, self.enum_value_map[self.value])
