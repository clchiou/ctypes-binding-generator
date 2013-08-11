'''Parse and generate ctypes binding from C sources with clang.'''

from cbind.source import SyntaxTreeForest
from cbind.passes import (scan_required_nodes, scan_forward_decl,
        scan_va_list_tag, scan_anonymous_pod)
from cbind.codegen import gen_tree_node, gen_record
import cbind.annotations as annotations


class CtypesBindingGenerator:
    '''Generate ctypes binding from C source files with libclang.'''

    def __init__(self):
        '''Initialize the object.'''
        self.syntax_tree_forest = SyntaxTreeForest()

    def parse(self, path, contents=None, args=None):
        '''Call parser.parse().'''
        syntax_tree = self.syntax_tree_forest.parse(path,
                contents=contents, args=args)
        scan_required_nodes(syntax_tree, path)
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
