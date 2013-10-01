# Copyright (C) 2013 Che-Liang Chiou.

'''Generate ctypes binding from syntax tree.'''

from cbind.codegen.helper import gen_tree_node, gen_record
from cbind.codegen.helper import make_function_argtypes, make_function_restype
from cbind.codegen.helper import set_cpp_binding
