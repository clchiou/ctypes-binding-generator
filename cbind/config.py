'''Parse config data.'''

from collections import namedtuple
import logging
import re
import types

from cbind.cindex import CursorKind
from cbind.codegen import make_function_argtypes, make_function_restype
import cbind.annotations as annotations


class SyntaxTreeMatcher(namedtuple('SyntaxTreeMatcher', '''
        argtypes
        errcheck
        method
        mixin
        name
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
        rename = spec.get('rename')
        if rename:
            if type(rename) in types.StringTypes:
                rename = [(re.compile(spec['name']), rename)]
            else:
                rename_rules = []
                for blob in rename:
                    pattern = re.compile(blob[0])
                    if len(blob) == 2:
                        replace = blob[1]
                    else:
                        replace = eval(blob[1], {})
                    rename_rules.append((pattern, replace))
                rename = rename_rules
        # pylint: disable=W0142
        return cls(rename=rename,
                errcheck=spec.get('errcheck'),
                method=spec.get('method'),
                mixin=spec.get('mixin'),
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

    def do_import(self, tree):
        '''Check if this tree should be imported.'''
        return self.do_match(tree)

    def do_rename(self, tree):
        '''Rename tree.'''
        if not self.do_match(tree):
            return False
        if not self.name or not self.rename:
            logging.info('Could not rename with no rename rule')
            return True
        new_name = tree.name
        for pattern, replace in self.rename:
            new_name = pattern.sub(replace, new_name)
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

    def do_mixin(self, tree):
        '''Mix in classes.'''
        if not self.do_match(tree):
            return False
        if not self.mixin:
            logging.info('Could not mix in empty class list')
            return True
        tree.annotate(annotations.MIXIN, self.mixin)
        return True


class MatcherAggregator(list):
    '''Aggregate of matchers.'''

    def do_action(self, tree, method):
        '''Run an OR operation on matchers.'''
        for matcher in self:
            if method(matcher, tree):
                return True
        return False


def _make_doer(method):
    '''Make doer.'''
    return lambda self, tree: self.do_action(tree, method)
for _name, _method in vars(SyntaxTreeMatcher).iteritems():
    if _name.startswith('do_'):
        setattr(MatcherAggregator, _name, _make_doer(_method))
