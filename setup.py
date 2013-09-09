#!/usr/bin/env python

from distutils.core import setup

setup(
    name='ctypes-binding-generator',
    version='0.4.0',
    description='Generate ctypes binding from C source files',
    author='Che-Liang Chiou',
    author_email='clchiou@gmail.com',
    license='GNU GPLv3',
    url='https://github.com/clchiou/ctypes-binding-generator',
    packages=['cbind', 'cbind/passes', 'pycbind'],
    scripts=['bin/cbind'],
)
