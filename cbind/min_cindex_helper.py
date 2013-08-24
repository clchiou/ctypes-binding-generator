'''Helpers for _clang_index module.'''

import cbind._clang_index
import cbind.min_cindex


def ref_translation_unit(result, _, arguments):
    '''Store a reference to TranslationUnit in the Python object so that
    it is not GC'ed before this cursor.'''
    # pylint: disable=W0212
    tunit = None
    for arg in arguments:
        if isinstance(arg, cbind.min_cindex.TranslationUnit):
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
    # pylint: disable=W0212
    if result == cbind._clang_index.clang_getNullCursor():
        return None
    return ref_translation_unit(result, function, arguments)
