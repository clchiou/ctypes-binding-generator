# Copyright (C) 2013 Che-Liang Chiou.

'''Package for automatic generation of ctypes bindings from C sources.'''


CLANG_CINDEX    = 'clang-cindex'
MIN_CINDEX      = 'min-cindex'


# Default choose min_cindex
_CINDEX_IMPL_CHOICE = MIN_CINDEX


def choose_cindex_impl(choice=None):
    '''Set/get cindex implementation choice.'''
    global _CINDEX_IMPL_CHOICE  # pylint: disable=W0603
    if choice:
        _CINDEX_IMPL_CHOICE = choice
    return _CINDEX_IMPL_CHOICE


def _parse_args(args=None):
    '''Parse command-line arguments.'''
    import argparse
    parser = argparse.ArgumentParser(description='''
            Generate ctypes binding from C source files with clang.
            ''')
    parser.add_argument('-v', action='count', default=0,
            help='increase verbosity level')
    parser.add_argument('-i', metavar='SOURCE', action='append',
            help='C source file')
    parser.add_argument('-o', metavar='OUTPUT', default='-',
            help='output file, default to \'-\' (stdout)')
    parser.add_argument('--config', type=argparse.FileType('r'),
            help='configuration file')
    parser.add_argument('--cindex', default=MIN_CINDEX,
            choices=[MIN_CINDEX, CLANG_CINDEX],
            help='choose cindex implementation')
    parser.add_argument('-l', metavar='LIBRARY',
            help='library name; use default loader codes')

    group = parser.add_argument_group(title='macro parser arguments',
            description='''
            Translate C macros into Python codes (experimental). The PATTERN
            argument will match macro name.
            ''')
    group.add_argument('--enable-macro', action='store_true',
            help='enable macro translation')
    group.add_argument('--macro-int', metavar='PATTERN',
            help='assure that these macros are integer constants')

    parser.add_argument('ccargs', metavar='CCARGS', nargs=argparse.REMAINDER,
            help='arguments passed to clang, separated by an optional \'--\' '
                 'from those passed to %(prog)s')

    args = parser.parse_args(args=args)
    return parser, args


def main(args=None):
    '''Main function.'''
    import logging
    import sys

    parser, args = _parse_args(args=args)
    if not args.i:
        parser.print_usage()
        return 0

    logging.basicConfig(format='%(filename)s: %(message)s')
    if args.v > 0:
        logging.getLogger().setLevel(logging.INFO)

    if args.ccargs and args.ccargs[0] == '--':
        clang_args = args.ccargs[1:]
    else:
        clang_args = args.ccargs

    choose_cindex_impl(args.cindex)
    from cbind.ctypes_binding import CtypesBindingGenerator
    from cbind.macro import MacroGenerator

    cbgen = CtypesBindingGenerator()
    if args.config:
        try:
            import yaml
        except ImportError:
            parser.error('could not load Python package yaml')
        cbgen.config(yaml.load(args.config))

    for c_src in args.i:
        cbgen.parse(c_src, args=clang_args)
    if args.enable_macro:
        mcgen = MacroGenerator(macro_int=args.macro_int)
        for c_src in args.i:
            mcgen.parse(c_src, args=clang_args)

    if args.o == '-':
        output = sys.stdout
    else:
        output = open(args.o, 'w')
    with output:
        cbgen.generate_preamble(parser.prog, args.l, output)
        cbgen.generate(output)
        if args.enable_macro:
            mcgen.generate(output)

    return 0
