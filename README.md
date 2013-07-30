ctypes-binding-generator
========================

**ctypes-binding-generator** is a Python package to generate ctypes binding
from C source files.  It requires libclang and clang Python binding to parse
source files.

Examples
--------

ctypes-binding-generator includes a small command-line program called
**cbind**.  You may use it to generate ctypes binding for, say, stdio.h.

    $ cbind -i /usr/include/stdio.h -o stdio.py --prolog-str '_lib = cdll.LoadLibrary("libc.so.6")'

Then you may test the generated ctypes binding of stdio.h.

    $ python -c 'import stdio; stdio.printf("hello world\n")'
    hello world

### Macros ###

Since macros are an important part of C headers, cbind may translate
simple C macros to Python codes.  For those complicated macros that cbind
cannot understand, you have to translate them manually.  Let's consider
Linux input.h header as an example, and write a small program that dumps
input events, such as mouse movements.

To enable macro translation, just provide --macro-enable flag to cbind.

    $ cbind -i /usr/include/linux/input.h -o demo/linux_input.py -v --macro-enable
    macro.py: Could not parse macro: #define EVIOCGID _IOR('E', 0x02, struct input_id)
    macro.py: Could not parse macro: #define EVIOCGREP _IOR('E', 0x03, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCSREP _IOW('E', 0x03, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCGKEYCODE _IOR('E', 0x04, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCGKEYCODE_V2 _IOR('E', 0x04, struct input_keymap_entry)
    macro.py: Could not parse macro: #define EVIOCSKEYCODE _IOW('E', 0x04, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCSKEYCODE_V2 _IOW('E', 0x04, struct input_keymap_entry)
    macro.py: Could not parse macro: #define EVIOCGABS(abs) _IOR('E', 0x40 + (abs), struct input_absinfo)
    macro.py: Could not parse macro: #define EVIOCSABS(abs) _IOW('E', 0xc0 + (abs), struct input_absinfo)
    macro.py: Could not parse macro: #define EVIOCSFF _IOC(_IOC_WRITE, 'E', 0x80, sizeof(struct ff_effect))
    macro.py: Could not resolve reference to "_IOR" in #define EVIOCGVERSION _IOR('E', 0x01, int)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGNAME(len) _IOC(_IOC_READ, 'E', 0x06, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGPHYS(len) _IOC(_IOC_READ, 'E', 0x07, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGUNIQ(len) _IOC(_IOC_READ, 'E', 0x08, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGPROP(len) _IOC(_IOC_READ, 'E', 0x09, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGMTSLOTS(len) _IOC(_IOC_READ, 'E', 0x0a, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGKEY(len) _IOC(_IOC_READ, 'E', 0x18, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGLED(len) _IOC(_IOC_READ, 'E', 0x19, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGSND(len) _IOC(_IOC_READ, 'E', 0x1a, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGSW(len) _IOC(_IOC_READ, 'E', 0x1b, len)
    macro.py: Could not resolve reference to "_IOC" in #define EVIOCGBIT(ev, len) _IOC(_IOC_READ, 'E', 0x20 + (ev), len)
    macro.py: Could not resolve reference to "_IOW" in #define EVIOCRMFF _IOW('E', 0x81, int)
    macro.py: Could not resolve reference to "_IOR" in #define EVIOCGEFFECTS _IOR('E', 0x84, int)
    macro.py: Could not resolve reference to "_IOW" in #define EVIOCGRAB _IOW('E', 0x90, int)
    macro.py: Could not resolve reference to "_IOW" in #define EVIOCSCLOCKID _IOW('E', 0xa0, int)

Note that we provide -v flag to cbind, which enables verbose output, and
cbind reports macros that it cannot understand.  However, not all of them
are incomprehensible to cbind - it just needs some hints.  Let's look at the
"Could not resolve reference" messages first.  Because cbind only tries to
translate macros in the header you provide, for macros defined in other headers
that are referenced, cbind will complain about them.  While cbind *should*
search recursively for these foreign macro definitions, this feature is not
implemented for now.  So let's tell cbind the pattern of the names of the
macros through --macro-include PATTERN flag.  PATTERN is regular expression
that will match macro names.

    $ cbind -i /usr/include/linux/input.h -o demo/linux_input.py -v --macro-enable --macro-include _IO
    macro.py: Could not parse macro: #define EVIOCGID _IOR('E', 0x02, struct input_id)
    macro.py: Could not parse macro: #define EVIOCGREP _IOR('E', 0x03, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCSREP _IOW('E', 0x03, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCGKEYCODE _IOR('E', 0x04, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCGKEYCODE_V2 _IOR('E', 0x04, struct input_keymap_entry)
    macro.py: Could not parse macro: #define EVIOCSKEYCODE _IOW('E', 0x04, unsigned int[2])
    macro.py: Could not parse macro: #define EVIOCSKEYCODE_V2 _IOW('E', 0x04, struct input_keymap_entry)
    macro.py: Could not parse macro: #define EVIOCGABS(abs) _IOR('E', 0x40 + (abs), struct input_absinfo)
    macro.py: Could not parse macro: #define EVIOCSABS(abs) _IOW('E', 0xc0 + (abs), struct input_absinfo)
    macro.py: Could not parse macro: #define EVIOCSFF _IOC(_IOC_WRITE, 'E', 0x80, sizeof(struct ff_effect))

Okay, cbind does not complain about unresolved references.  Now what?
Actually, cbind may translate constant integer expressions, but you have
to tell cbind where to look through --macro-int PATTERN flag.

    $ cbind -i /usr/include/linux/input.h -o demo/linux_input.py -v --macro-enable --macro-include _IO --macro-int EVIO
    macro.py: Could not parse macro: #define EVIOCGABS(abs) _IOR('E', 0x40 + (abs), struct input_absinfo)
    macro.py: Could not parse macro: #define EVIOCSABS(abs) _IOW('E', 0xc0 + (abs), struct input_absinfo)

We reduce the macros that cbind cannot understand to two.  It is good
enough for now.  Let's manually translate them to Python codes and move on.

    EVIOCGABS = lambda abs: _IOR(ord('E'), 0x40 + abs, input_absinfo)
    EVIOCSABS = lambda abs: _IOW(ord('E'), 0xc0 + abs, input_absinfo)

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
