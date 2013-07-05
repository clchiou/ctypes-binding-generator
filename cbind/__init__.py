'''Package for automatic generation of ctypes bindings from C sources.'''

from ctypes_binding import CtypesBindingGenerator
from macro_const import MacroConstantsGenerator


def parse_args():
    '''Parse command-line arguments.'''
    import argparse
    import re
    parser = argparse.ArgumentParser(
            description='Generate ctypes binding from C source files '
                        'with clang.')
    parser.add_argument('-v', action='count', default=0,
            help='verbosity')
    parser.add_argument('-i', metavar='SOURCE', action='append',
            help='C source file')
    parser.add_argument('-o', metavar='OUTPUT', default='-',
            help='output file, default to \'-\' (stdout)')
    parser.add_argument('--variable', metavar='VAR', default='_lib',
            help='name of the variable for the shared library object')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--prolog', metavar='FILE', type=file,
            help='prolog of generated Python output')
    group.add_argument('--prolog-str', metavar='STR')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--epilog', metavar='FILE', type=file,
            help='epilog of generated Python output')
    group.add_argument('--epilog-str', metavar='STR')
    parser.add_argument('--symbol', metavar='+/-SYM', action='append',
            help='include/exclude symbol when generating output')
    parser.add_argument('--parse-macro', action='store_true',
            help='generate Python codes from macro constants (experimental)')
    parser.add_argument('--macro-int', metavar='REGEX', type=re.compile,
            help='assure that macro matched by REGEX are integer-typed')
    parser.add_argument('ccargs', metavar='CCARGS', nargs=argparse.REMAINDER,
            help='arguments passed to clang, separated by an optional \'--\' '
                 'from those passed to %(prog)s')
    args = parser.parse_args()
    return parser, args


def parse_symbol_arg(parser, args):
    '''Parse the --symbol command-line argument.'''
    included_symbols = set()
    excluded_symbols = set()
    if not args.symbol:
        return included_symbols, excluded_symbols
    for symbol in args.symbol:
        if symbol[0] == '-' and len(symbol) > 1:
            excluded_symbols.add(symbol[1:])
        elif symbol[0] == '+' and len(symbol) > 1:
            included_symbols.add(symbol[1:])
        else:
            included_symbols.add(symbol)
    if included_symbols & excluded_symbols:
        parser.error('symbol(s) is added to both included and excluded list.')
    return included_symbols, excluded_symbols


def make_section(target, args, output):
    '''Make prolog/epilog.'''
    for attr in (target, target + '_str'):
        section = getattr(args, attr)
        if not section:
            continue
        if hasattr(section, 'read'):
            output.write(section.read())
        else:
            output.write('%s\n' % section)
        output.write('\n')
        break


def main():
    '''Main function.'''
    import logging
    import sys

    parser, args = parse_args()
    if not args.i:
        parser.print_usage()
        return 0

    if args.v > 0:
        logging.getLogger().setLevel(logging.INFO)

    included_symbols, excluded_symbols = parse_symbol_arg(parser, args)

    if args.ccargs and args.ccargs[0] == '--':
        clang_args = args.ccargs[1:]
    else:
        clang_args = args.ccargs

    cbgen = CtypesBindingGenerator(args.variable)
    for c_src in args.i:
        cbgen.parse(c_src, args=clang_args)
    if args.parse_macro:
        mcgen = MacroConstantsGenerator()
        for c_src in args.i:
            mcgen.preprocess(c_src)
        mcgen.parse(args=clang_args,
                included_symbols=included_symbols,
                excluded_symbols=excluded_symbols,
                regex_integer_typed=args.macro_int)

    if args.o == '-':
        output = sys.stdout
    else:
        output = open(args.o, 'w')
    with output:
        output.write('# This is generated by %s and should not be edited.\n'
                'from ctypes import *\n\n' % parser.prog)
        make_section('prolog', args, output)
        cbgen.generate(output,
                included_symbols=included_symbols,
                excluded_symbols=excluded_symbols)
        if args.parse_macro:
            mcgen.generate(output)
        make_section('epilog', args, output)

    return 0
