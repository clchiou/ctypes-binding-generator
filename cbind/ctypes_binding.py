'''Parse and generate ctypes binding from C sources with clang.'''

import functools
from cbind.codegen import gen_tree_node, gen_record
from cbind.config import SyntaxTreeMatcher
from cbind.passes import (scan_required_nodes,
        scan_and_rename,
        scan_forward_decl,
        scan_va_list_tag,
        scan_anonymous_pod)
from cbind.source import SyntaxTreeForest
import cbind.annotations as annotations


class CtypesBindingGenerator:
    '''Generate ctypes binding from C source files with libclang.'''

    def __init__(self):
        '''Initialize the object.'''
        self.syntax_tree_forest = SyntaxTreeForest()
        self.check_required = check_locally_defined
        self.rename = None

    def config(self, config_data):
        '''Configure the generator.'''
        if 'import' in config_data:
            matcher = SyntaxTreeMatcher.make(config_data['import'])
            self.check_required = matcher.match
        if 'rename' in config_data:
            self.rename = SyntaxTreeMatcher.make(config_data['rename']).rename

    def parse(self, path, contents=None, args=None):
        '''Call parser.parse().'''
        if self.check_required is check_locally_defined:
            check_required = functools.partial(check_locally_defined, path=path)
        else:
            check_required = self.check_required

        syntax_tree = self.syntax_tree_forest.parse(path,
                contents=contents, args=args)
        scan_required_nodes(syntax_tree, check_required)
        if self.rename:
            scan_and_rename(syntax_tree, self.rename)
        scan_forward_decl(syntax_tree)
        scan_va_list_tag(syntax_tree)
        scan_anonymous_pod(syntax_tree)

    def get_translation_units(self):
        '''Get translation units.'''
        for syntax_tree in self.syntax_tree_forest:
            yield syntax_tree.translation_unit

    def generate(self, output):
        '''Generate ctypes binding.'''
        for syntax_tree in self.syntax_tree_forest:
            va_list_tag = syntax_tree.get_annotation(
                    annotations.USE_VA_LIST_TAG, False)
            if va_list_tag:
                gen_record(va_list_tag, output,
                        declared=False, declaration=False)
                output.write('\n')
                break
        for syntax_tree in self.syntax_tree_forest:
            syntax_tree.traverse(
                    preorder=lambda tree: self._gen_forward_decl(tree, output),
                    postorder=lambda tree: gen_tree_node(tree, output))

    @staticmethod
    def _gen_forward_decl(tree, output):
        '''Generate forward declaration for nodes.'''
        if not tree.get_annotation(annotations.REQUIRED, False):
            return
        if not tree.get_annotation(annotations.FORWARD_DECLARATION, False):
            return
        declared = tree.get_annotation(annotations.DECLARED, False)
        gen_record(tree, output, declared=declared, declaration=True)
        tree.annotate(annotations.DECLARED, True)


def check_locally_defined(tree, path):
    '''Check if a node is locally defined.'''
    return tree.location.file and tree.location.file.name == path
