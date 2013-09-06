'''Parse config data.'''

from collections import namedtuple
import logging
import re
import types

from cbind.cindex import CursorKind
from cbind.codegen import make_function_argtypes, make_function_restype
import cbind.annotations as annotations


def call_do_match(func):
    '''Make a call to do_match().'''
    def wrapper(self, tree):
        '''Wrapper of func.'''
        if not self.do_match(tree):
            return False
        return func(self, tree)
    return wrapper


def check_matcher_data(field_names):
    '''Check if the matcher has these fields defined.'''
    def make_wrapper(func):
        '''Make wrapper.'''
        def wrapper(self, tree):
            '''Wrapper of func.'''
            call_func = True
            for name in field_names:
                if not getattr(self, name):
                    logging.info('Could not continue without %s', name)
                    call_func = False
            if call_func:
                return func(self, tree)
            else:
                return True
        return wrapper
    return make_wrapper


def make_annotator(annotation_name, field_name):
    '''Make annotator.'''
    def annotator(self, tree):
        '''annotator function.'''
        tree.annotate(annotation_name, getattr(self, field_name))
        return True
    return annotator


class SyntaxTreeMatcher(namedtuple('SyntaxTreeMatcher', '''
        argtypes
        enum
        errcheck
        import_
        method
        mixin
        name
        parent
        rename
        restype
        ''')):
    '''Match SyntaxTree node.'''

    # pylint: disable=E1101,W0232

    @classmethod
    def make(cls, matcher_specs):
        '''Create a sum of matchers.'''
        matchers = tuple(cls._make(spec) for spec in matcher_specs)
        return MatcherAggregator(matchers)

    @classmethod
    def _make(cls, spec):
        '''Create a matcher.'''
        patterns = {}
        if 'argtypes' in spec:
            patterns['argtypes'] = tuple(re.compile(regex, re.VERBOSE)
                    for regex in spec['argtypes'])
        else:
            patterns['argtypes'] = None
        if 'parent' in spec:
            patterns['parent'] = cls._make(spec['parent'])
        else:
            patterns['parent'] = None
        for attr in ('name', 'restype'):
            if attr in spec:
                val = re.compile(spec[attr], re.VERBOSE)
            else:
                val = None
            patterns[attr] = val
        if 'rename' in spec:
            rename = cls._make_rename_rules(spec)
        else:
            rename = None
        # pylint: disable=W0142
        return cls(rename=rename,
                enum=spec.get('enum'),
                errcheck=spec.get('errcheck'),
                import_=spec.get('import', True),
                method=spec.get('method'),
                mixin=spec.get('mixin'),
                **patterns)

    @staticmethod
    def _make_rename_rules(spec):
        '''Make rename rules.'''
        rename = spec['rename']
        if type(rename) in types.StringTypes:
            return [(re.compile(spec['name']), rename)]
        rename_rules = []
        for rule in rename:
            pattern = re.compile(rule['pattern'])
            if 'replace' in rule:
                replace = rule['replace']
            else:
                replace = eval(rule['function'], {})
            rename_rules.append((pattern, replace))
        return rename_rules

    def do_match(self, tree):
        '''Match tree.'''
        if (not self.argtypes and
            not self.name and
            not self.parent and
            not self.restype):
            logging.info('Could not match with empty rule')
            return False
        return ((not self.name or self._match_name(tree)) and
                (not self.argtypes or self._match_argtypes(tree)) and
                (not self.restype or self._match_restype(tree)) and
                (not self.parent or not tree.semantic_parent or
                 self.parent.do_match(tree.semantic_parent)))

    def _match_name(self, tree):
        '''Match tree.name.'''
        return tree.name and self.name.search(tree.name)

    def _match_argtypes(self, tree):
        '''Match tree.argtypes.'''
        if tree.kind != CursorKind.FUNCTION_DECL:
            return False
        argtypes = make_function_argtypes(tree)
        if len(self.argtypes) != len(argtypes):
            return False
        for argtype_search, argtype in zip(self.argtypes, argtypes):
            if not argtype_search.search(argtype):
                return False
        return True

    def _match_restype(self, tree):
        '''Match tree.restype.'''
        return (tree.kind == CursorKind.FUNCTION_DECL and
                self.restype.search(make_function_restype(tree)))

    @call_do_match
    def do_import(self, _):
        '''Check if this tree should be imported.'''
        if self.import_:
            return True
        raise StopIteration()

    @call_do_match
    @check_matcher_data(('name', 'rename'))
    def do_rename(self, tree):
        '''Rename tree.'''
        new_name = tree.name
        for pattern, replace in self.rename:
            new_name = pattern.sub(replace, new_name)
        if new_name == tree.name:
            return False
        tree.annotate(annotations.NAME, new_name)
        return True

    do_errcheck = call_do_match(
            check_matcher_data(('errcheck', ))(
                make_annotator(annotations.ERRCHECK, 'errcheck')))

    do_method = call_do_match(
            check_matcher_data(('method', ))(
                make_annotator(annotations.METHOD, 'method')))

    do_mixin = call_do_match(
            check_matcher_data(('mixin', ))(
                make_annotator(annotations.MIXIN, 'mixin')))

    do_enum = call_do_match(
            check_matcher_data(('enum', ))(
                make_annotator(annotations.ENUM, 'enum')))


class MatcherAggregator(list):
    '''Aggregate of matchers.'''

    def do_action(self, tree, method):
        '''Run an OR operation on matchers.'''
        try:
            for matcher in self:
                if method(matcher, tree):
                    return True
        except StopIteration:
            pass
        return False


def _make_doer(method):
    '''Make doer.'''
    return lambda self, tree: self.do_action(tree, method)
for _name, _method in vars(SyntaxTreeMatcher).iteritems():
    if _name.startswith('do_'):
        setattr(MatcherAggregator, _name, _make_doer(_method))
