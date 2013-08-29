'''Minimum implementation that is compitable with clang.cindex.'''

# pylint: disable=C0103,W0108,W0142

import cbind._clang_index as _index
from cbind._clang_index import Cursor, CursorKind, Type, TypeKind, LinkageKind
from cbind.min_cindex_helper import Index


__all__ = ['Index', 'Cursor', 'CursorKind', 'Type', 'TypeKind', 'LinkageKind']


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
