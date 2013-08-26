'''Parse and generate ctypes binding from C sources with clang.'''

import functools
from cbind.codegen import gen_tree_node, gen_record
from cbind.config import SyntaxTreeMatcher
from cbind.passes import (custom_pass,
        scan_required_nodes,
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
        self._config = {}

    def config(self, config_data):
        '''Configure the generator.'''
        if 'preamble' in config_data:
            self._config['preamble'] = config_data['preamble']
        for name in ('import', 'rename', 'errcheck', 'method', 'mixin'):
            if name in config_data:
                matcher = SyntaxTreeMatcher.make(config_data[name])
                self._config[name] = getattr(matcher, 'do_' + name)

    def parse(self, path, contents=None, args=None):
        '''Call parser.parse().'''
        if 'import' in self._config:
            check_required = self._config['import']
        else:
            check_required = functools.partial(check_locally_defined, path=path)

        syntax_tree = self.syntax_tree_forest.parse(path,
                contents=contents, args=args)
        scan_required_nodes(syntax_tree, check_required)
        if 'rename' in self._config:
            scan_and_rename(syntax_tree, self._config['rename'])
        scan_forward_decl(syntax_tree)
        scan_va_list_tag(syntax_tree)
        scan_anonymous_pod(syntax_tree)

        # Since now tree is "complete", we may attach information to it.
        for name in ('errcheck', 'method', 'mixin'):
            if name in self._config:
                custom_pass(syntax_tree, self._config[name])

    def get_translation_units(self):
        '''Get translation units.'''
        for syntax_tree in self.syntax_tree_forest:
            yield syntax_tree.translation_unit

    def generate(self, output):
        '''Generate ctypes binding.'''
        if 'preamble' in self._config:
            output.write(self._config['preamble'])
            output.write('\n')
        if 'method' in self._config:
            output.write('import types as _python_types\n')
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
