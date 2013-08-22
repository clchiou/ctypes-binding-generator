'''Parse config data.'''

from collections import namedtuple
from functools import partial
import logging
import re

from cbind.cindex import CursorKind
from cbind.codegen import make_function_argtypes, make_function_restype
import cbind.annotations as annotations


class SumOfMatchers(namedtuple('SumOfMatchers', 'matchers')):
    '''Aggregate of matchers.'''

    # pylint: disable=R0903,W0232

    def _or(self, tree, method=None):
        '''Run an OR operation on matchers.'''
        for matcher in self.matchers:  # pylint: disable=E1101
            if method(matcher, tree):
                return True
        return False

    def __getattr__(self, name):
        method = getattr(SyntaxTreeMatcher, name)
        return partial(self._or, method=method)


class SyntaxTreeMatcher(namedtuple('SyntaxTreeMatcher', '''
        name
        argtypes
        restype
        rewrite
        errcheck
        method
        ''')):
    '''Match SyntaxTree node.'''

    # pylint: disable=E1101,W0232

    @classmethod
    def make(cls, matcher_specs):
        '''Create a sum of matchers.'''
        matchers = tuple(cls._make(spec) for spec in matcher_specs)
        return SumOfMatchers(matchers=matchers)

    @classmethod
    def _make(cls, spec):
        '''Create a matcher.'''
        patterns = {'argtypes': None}
        if 'argtypes' in spec:
            patterns['argtypes'] = tuple(re.compile(regex, re.VERBOSE)
                    for regex in spec['argtypes'])
        for attr in ('name', 'restype'):
            if attr in spec:
                val = re.compile(spec[attr], re.VERBOSE)
            else:
                val = None
            patterns[attr] = val
        # pylint: disable=W0142
        return cls(rewrite=spec.get('rewrite'),
                errcheck=spec.get('errcheck'),
                method=spec.get('method'),
                **patterns)

    def do_match(self, tree):
        '''Match tree.'''
        if not self.name and not self.restype and not self.argtypes:
            logging.info('Could not match with empty rule')
            return False
        return ((not self.name or self._match_name(tree)) and
                (not self.argtypes or self._match_argtypes(tree)) and
                (not self.restype or self._match_restype(tree)))

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

    def do_rename(self, tree):
        '''Rename tree.'''
        if not self.do_match(tree):
            return False
        if not self.name or not self.rewrite:
            logging.info('Could not rename with no rewrite rule')
            return True
        new_name = self.name.sub(self.rewrite, tree.name)
        if new_name == tree.name:
            return False
        tree.annotate(annotations.NAME, new_name)
        return True

    def do_errcheck(self, tree):
        '''Attach errcheck.'''
        if not self.do_match(tree):
            return False
        if not self.errcheck:
            logging.info('Could not attach empty errcheck')
            return True
        tree.annotate(annotations.ERRCHECK, self.errcheck)
        return True

    def do_method(self, tree):
        '''Attach method.'''
        if not self.do_match(tree):
            return False
        if not self.method:
            logging.info('Could not attach empty method')
            return True
        tree.annotate(annotations.METHOD, self.method)
        return True
