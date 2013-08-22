'''Parse config data.'''

from collections import namedtuple
import logging
import re

from cbind.cindex import CursorKind
from cbind.codegen import make_function_restype
import cbind.annotations as annotations


class SumOfMatchers(namedtuple('SumOfMatchers', 'matchers')):
    '''Aggregate of matchers.'''

    # pylint: disable=R0903,W0232

    def _or(self, tree, method):
        '''Run an OR operation on matchers.'''
        for matcher in self.matchers:  # pylint: disable=E1101
            if method(matcher, tree):
                return True
        return False

    def do_match(self, tree):
        '''Match tree.'''
        return self._or(tree, SyntaxTreeMatcher.do_match)

    def do_rename(self, tree):
        '''Rename tree.'''
        return self._or(tree, SyntaxTreeMatcher.do_rename)

    def do_errcheck(self, tree):
        '''Attach errcheck.'''
        return self._or(tree, SyntaxTreeMatcher.do_errcheck)


class SyntaxTreeMatcher(namedtuple('SyntaxTreeMatcher', '''
        name
        restype
        rewrite
        errcheck
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
        patterns = {}
        for attr in ('name', 'restype'):
            if attr in spec:
                val = re.compile(spec[attr], re.VERBOSE)
            else:
                val = None
            patterns[attr] = val
        # pylint: disable=W0142
        return cls(rewrite=spec.get('rewrite'),
                errcheck=spec.get('errcheck'),
                **patterns)

    def do_match(self, tree):
        '''Match tree.'''
        if self.name:
            if not (tree.name and self.name.search(tree.name)):
                return False
        if self.restype:
            if not (tree.kind == CursorKind.FUNCTION_DECL and
                    self.restype.search(make_function_restype(tree))):
                return False
        return True

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
