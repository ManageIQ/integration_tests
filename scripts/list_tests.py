#!/usr/bin/env python2

from __future__ import unicode_literals
import os
import os.path
import sys
import re

if len(sys.argv) == 1:
    print("""
Invoke either by supplying a path or a file and optionally a string to find in a test name

e.g. list_test . provision
e.g. list_test file.py
""")
    sys.exit(1)


def parser(filename, exp=None):
    try:
        with open(filename, 'r') as f:
            data = f.read()
    except IOError:
        data = ""

    if not exp:
        exp = ""

    p = re.findall('\s*def\s*[a-zA-Z0-9_]*?(test_.*?{}.*?)\('.format(exp), data)
    for test in p:
        if isinstance(test, basestring):
            print("{} :: {}".format(filename, test))
        else:
            print("{} :: {}".format(filename, test[0]))

exp = None
if len(sys.argv) == 3:
    exp = sys.argv[2]

if sys.argv[1].endswith('.py'):
    parser(sys.argv[1], exp)
else:
    files = [os.path.join(d, fn) for d, dn, fns in os.walk(sys.argv[1]) for fn in fns]

    for filename in files:
        if filename.endswith('.py'):
            parser(filename, exp)
