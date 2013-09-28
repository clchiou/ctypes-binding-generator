# Copyright (C) 2013 Che-Liang Chiou.

'''Compatibility layer of Python 2.7'''

import sys

__all__ = ['StringIO']


if sys.version_info.major == 3:
    from io import StringIO
    decode_str = bytes.decode   # pylint: disable=C0103
else:
    from cStringIO import StringIO
    decode_str = str            # pylint: disable=C0103
