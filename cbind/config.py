'''Parse config data.'''

from collections import namedtuple
import re


class SumOfMatchers(namedtuple('SumOfMatchers', 'matchers')):
    '''Aggregate of matchers.'''

    # pylint: disable=R0903,W0232

    def match(self, tree):
        '''Match tree.'''
        for matcher in self.matchers:  # pylint: disable=E1101
            result = matcher.match(tree)
            if result:
                return result
        return None


class SyntaxTreeMatcher(namedtuple('SyntaxTreeMatcher', 'name')):
    '''Match SyntaxTree node.'''

    # pylint: disable=W0232

    @classmethod
    def make(cls, matcher_specs):
        '''Create a matcher.'''
        matchers = tuple(cls(name=re.compile(spec['name'], re.VERBOSE))
                for spec in matcher_specs)
        return SumOfMatchers(matchers=matchers)

    def match(self, tree):
        '''Match tree.'''
        # pylint: disable=E1101
        return tree.name and self.name.search(tree.name)
