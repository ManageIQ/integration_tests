#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import sys

if len(sys.argv) == 1:
    print(
        """Usage: {} arg1 arg2 ... argN\narg is either a string or int, depending on whether """
        """digging in dict or a list""".format(sys.argv[0]))
    exit(0)

result = json.loads(sys.stdin.read())

try:
    for arg in sys.argv[1:]:
        if isinstance(result, dict):
            result = result[arg]
        elif isinstance(result, list):
            result = result[int(arg)]
        else:
            print("Cannot apply {} to {}".format(str(arg), str(result)))
            exit(1)
except Exception as e:
    print("{}\t{}".format(type(e).__name__, str(e)))
    exit(2)

print(result)
