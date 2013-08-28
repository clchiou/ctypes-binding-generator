'''Minimum implementation that is compitable with clang.cindex.'''

# pylint: disable=C0103,W0108,W0142

import collections
from ctypes import c_char_p, c_void_p

import cbind._clang_index as _index
from cbind._clang_index import Cursor, CursorKind, Type, TypeKind, LinkageKind


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind', 'LinkageKind']


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


### Add enum tables


def add_enum_constants(cls, prefix):
    '''Add enum constants to class.'''
    cls_name = cls.__name__
    name_mapping = {}
    for name, value in vars(_index).iteritems():
        if name.startswith(prefix):
            new_name = name[len(prefix):]
            setattr(cls, new_name, cls(value))
            name_mapping[value] = new_name
    def to_str(self):
        '''Convert enum value to its name.'''
        return '%s.%s' % (cls_name, name_mapping[self.value])
    cls.__str__ = to_str

add_enum_constants(CursorKind, 'CURSOR_')
add_enum_constants(TypeKind, 'TYPE_')
add_enum_constants(LinkageKind, 'LINKAGE_')
