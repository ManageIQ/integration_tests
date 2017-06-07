#!/usr/bin/env python
"""
outputs the frozen packages
"""
from __future__ import print_function
import sys
import os
import argparse
import subprocess
import tempfile
import shutil
parser = argparse.ArgumentParser(description=__doc__.strip())
parser.add_argument('--venv', default=None)
parser.add_argument('--keep-venv', action='store_true')
parser.add_argument(
    "--template", default="requirements/template.txt",)
parser.add_argument(
    "--out", default=None,
    help='the file where packages should be written to')


def main(args):
    if args.venv is None:
        args.venv = tempfile.mkdtemp(suffix='-miq-QE-rebuild-venv')

    try:
        if not os.path.isdir(os.path.join(args.venv, 'bin')):
            subprocess.check_call([
                sys.executable, '-m', 'virtualenv', args.venv
            ])
        subprocess.check_call([
            os.path.join(args.venv, 'bin/pip'),
            'install', '-U', '-r', args.template])

        if args.out is None:
            subprocess.check_call([
                os.path.join(args.venv, 'bin/pip'), 'freeze'
            ], stdout=sys.stdout)
        else:
            with open(args.out, 'w') as out:
                subprocess.check_call([
                    os.path.join(args.venv, 'bin/pip'), 'freeze'
                ], stdout=out)

    finally:
        if not args.keep_venv:
            shutil.rmtree(args.venv)


if __name__ == '__main__':
    main(parser.parse_args())
