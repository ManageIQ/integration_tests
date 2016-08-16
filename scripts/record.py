#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Video recording script.

Use when you want to record something separately
"""
from __future__ import unicode_literals
import time
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from utils.video import Recorder


parser = ArgumentParser(
    epilog=__doc__,
    formatter_class=RawDescriptionHelpFormatter
)

parser.add_argument("filename", help="File name to save the recording in")
parser.add_argument("--display", default=None, type=str, help="Display to record")
parser.add_argument("--quality", default=None, type=int, help="Recording quality")
args = parser.parse_args()

with Recorder(args.filename, args.display, args.quality):
    alive = True
    while alive:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            alive = False
        except:
            pass
