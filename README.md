ctypes-binding-generator
========================

**ctypes-binding-generator** is a Python package to generate ctypes binding
from C source files.  It requires libclang and clang Python binding to parse
source files.

Examples
--------

ctypes-binding-generator includes a small command-line program called
**cbind**.  You may use it to generate ctypes binding for, say, stdio.h.

    $ cbind -i /usr/include/stdio.h -o stdio.py -l libc.so.6 \
        -- -I/usr/local/lib/clang/3.4/include

Note that you need /usr/local/lib/clang/3.4/include for stddef.h, etc.
Then you may test the generated ctypes binding of stdio.h.

    $ python -c 'import stdio; stdio.printf("hello world\n")'
    hello world

### Macros ###

Since macros are an important part of C headers, cbind may translate
simple C macros to Python codes.  For those complicated macros that cbind
cannot understand, you have to translate them manually.  Let's consider
Linux input.h header as an example, and write a small program that dumps
input events, such as mouse movements.

To enable macro translation, just provide --enable-macro flag to cbind.

    $ cbind -i /usr/include/linux/input.h -o demo/linux_input.py -v --enable-macro \
        -- -I/usr/local/lib/clang/3.4/include
    macro.py: Could not parse macro: #define EVIOCGID (((2U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x02)) << 0) | ((((sizeof(struct input_id)))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCGREP (((2U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x03)) << 0) | ((((sizeof(unsigned int[2])))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCSREP (((1U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x03)) << 0) | ((((sizeof(unsigned int[2])))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCGKEYCODE (((2U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x04)) << 0) | ((((sizeof(unsigned int[2])))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCGKEYCODE_V2 (((2U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x04)) << 0) | ((((sizeof(struct input_keymap_entry)))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCSKEYCODE (((1U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x04)) << 0) | ((((sizeof(unsigned int[2])))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCSKEYCODE_V2 (((1U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x04)) << 0) | ((((sizeof(struct input_keymap_entry)))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCGABS(abs) (((2U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x40 + (abs))) << 0) | ((((sizeof(struct input_absinfo)))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCSABS(abs) (((1U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0xc0 + (abs))) << 0) | ((((sizeof(struct input_absinfo)))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCSFF (((1U) << (((0 +8)+8)+14)) | (('E') << (0 +8)) | ((0x80) << 0) | ((sizeof(struct ff_effect)) << ((0 +8)+8)))

Note that we provide -v flag to cbind, which enables verbose output, and
cbind reports macros that it cannot understand.  However, not all of them
are incomprehensible to cbind - it just needs some hints.  cbind may translate
constant integer expressions, thanks to Clang, but you have to tell cbind
which macros are indeed integer expressions with --macro-int.

    $ cbind -i /usr/include/linux/input.h -o demo/linux_input.py -v --enable-macro --macro-int EVIO \
        -- -I/usr/local/lib/clang/3.4/include
    macro.py: Could not parse macro: #define EVIOCGABS(abs) (((2U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0x40 + (abs))) << 0) | ((((sizeof(struct input_absinfo)))) << ((0 +8)+8)))
    macro.py: Could not parse macro: #define EVIOCSABS(abs) (((1U) << (((0 +8)+8)+14)) | ((('E')) << (0 +8)) | (((0xc0 + (abs))) << 0) | ((((sizeof(struct input_absinfo)))) << ((0 +8)+8)))

For the remaining two macros you have to translate manually:

    EVIOCGABS = lambda abs: (2 << 30) | (ord('E') << 8) | (0x40 + abs) | (sizeof(input_absinfo) << 16)
    EVIOCSABS = lambda abs: (1 << 30) | (ord('E') << 8) | (0xc0 + abs) | (sizeof(input_absinfo) << 16)

Under demo/ directory there is the **evtest** program which uses the
linux\_input.py binding we generated.  It will require root permission to
access device file.  Press Ctrl-C to break evtest.

    $ sudo demo/evtest /dev/input/event0
    input driver version     : 1.0.1
    input device ID          : bus 0x3 vendor 0x46d product 0xc05b version 0x111
    input device name        : 'Logitech USB Optical Mouse'
    supported events:
      event type 0 (Sync)
      event type 1 (Key)
        event code 272 (LeftBtn)
        event code 273 (RightBtn)
        event code 274 (MiddleBtn)
        event code 275 (SideBtn)
        event code 276 (ExtraBtn)
        event code 277 (ForwardBtn)
        event code 278 (BackBtn)
        event code 279 (TaskBtn)
      event type 2 (Relative)
        event code 0 (X)
        event code 1 (Y)
        event code 6 (HWheel)
        event code 8 (Wheel)
      event type 4 (Misc)
        event code 4 (ScanCode)
    testing ... (interrupt to exit)
    event: time 1374999609.141463, type 2 (Relative), code 0 (X), value 1
    event: time 1374999609.141466, type 2 (Relative), code 1 (Y), value -1
    event: time 1374999609.141472, -------------- Report Sync ------------
    event: time 1374999609.149452, type 2 (Relative), code 0 (X), value 4
    event: time 1374999609.149454, type 2 (Relative), code 1 (Y), value -1
    event: time 1374999609.149459, -------------- Report Sync ------------
    ^C

You should see evtest shows driver and device info, supported events,
and dumps input events.
