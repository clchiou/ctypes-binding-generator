# Copyright (C) 2013 Che-Liang Chiou.

'''Generate ctypes binding from syntax tree.'''

from cbind.codegen.helper import gen_tree_node, gen_record
from cbind.codegen.helper import make_function_argtypes, make_function_restype
import cbind.annotations as annotations


class CodeGen:
    '''Generate ctypes binding from syntax tree.'''

    # Generate C++ bindings
    # TODO: Because C++ binding generation is an experimental feature, we would
    # not like to generate C++ binding without user consent.  But we will remove
    # this check when this feature is completed and not experimental.
    ENABLE_CPP = False

    ASSERT_LAYOUT = False

    make_function_argtypes = staticmethod(make_function_argtypes)
    make_function_restype = staticmethod(make_function_restype)

    def __init__(self):
        self.output = None

    def set_output(self, output):
        '''Set output buffer.'''
        self.output = output

    def generate(self, tree):
        '''Generate ctypes binding of a syntax tree.'''
        gen_tree_node(tree, self.output)

    def generate_record_definition(self, tree):
        '''Generate definition of record (struct, union, or class).'''
        declared = tree.get_annotation(annotations.DECLARED, False)
        gen_record(tree, self.output, declared=declared, declaration=False)
        tree.annotate(annotations.DECLARED, True)
        tree.annotate(annotations.DEFINED, True)

    def generate_record_forward_decl(self, tree):
        '''Generate forward declaration of record (struct, union, or class).'''
        if not tree.get_annotation(annotations.REQUIRED, False):
            return
        if not tree.get_annotation(annotations.FORWARD_DECLARATION, False):
            return
        declared = tree.get_annotation(annotations.DECLARED, False)
        gen_record(tree, self.output, declared=declared, declaration=True)
        tree.annotate(annotations.DECLARED, True)
