#!/usr/bin/env python3
"""Video recording script.

Use when you want to record something separately
"""
import time
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from cfme.utils.video import Recorder


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
        except Exception:
            pass
