ctypes-binding-generator
========================

**ctypes-binding-generator** is a Python package to generate ctypes binding
from C source files.  It requires libclang and clang Python binding to parse
source files.

Examples
--------

**ctypes-binding-generator** includes a small command-line program called
**cbind**.  You may use it to generate ctypes binding for, say, stdio.h.

    $ cbind -i /usr/include/stdio.h -o stdio.py --prolog-str '_lib = cdll.LoadLibrary("libc.so.6")'

Then you may test the generated ctypes binding of stdio.h.

    $ python -c 'import stdio; stdio.printf("hello world\n")'
    hello world
