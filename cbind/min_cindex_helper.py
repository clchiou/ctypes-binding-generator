'''Helpers for _clang_index module.'''


def ref_translation_unit(result, _, arguments):
    '''Store a reference to TranslationUnit in the Python object so that
    it is not GC'ed before this cursor.'''
    from cbind.min_cindex import TranslationUnit
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
    from cbind._clang_index import clang_getNullCursor
    if result == clang_getNullCursor():
        return None
    return ref_translation_unit(result, function, arguments)
