'''Parse config data.'''

from collections import namedtuple
import re
import cbind.annotations as annotations


class SumOfMatchers(namedtuple('SumOfMatchers', 'matchers')):
    '''Aggregate of matchers.'''

    # pylint: disable=R0903,W0232

    def _or(self, tree, method, none_of_them):
        '''Run an OR operation on matchers.'''
        for matcher in self.matchers:  # pylint: disable=E1101
            result = method(matcher, tree)
            if result:
                return result
        return none_of_them

    def match(self, tree):
        '''Match tree.'''
        return self._or(tree, SyntaxTreeMatcher.match, None)

    def rename(self, tree):
        '''Rename tree.'''
        return self._or(tree, SyntaxTreeMatcher.rename, False)


class SyntaxTreeMatcher(namedtuple('SyntaxTreeMatcher', 'name rewrite')):
    '''Match SyntaxTree node.'''

    # pylint: disable=E1101,W0232

    @classmethod
    def make(cls, matcher_specs):
        '''Create a matcher.'''
        matchers = tuple(
                cls(name=re.compile(spec['name'], re.VERBOSE),
                    rewrite=spec.get('rewrite'))
                for spec in matcher_specs)
        return SumOfMatchers(matchers=matchers)

    def match(self, tree):
        '''Match tree.'''
        return tree.name and self.name.search(tree.name)

    def rename(self, tree):
        '''Rename tree.'''
        if self.rewrite is None:
            raise ValueError('Could not rename to None')
        if not tree.name:
            return False
        if not self.match(tree):
            return False
        new_name = self.name.sub(self.rewrite, tree.name)
        if new_name == tree.name:
            return False
        tree.annotate(annotations.NAME, new_name)
        return True
