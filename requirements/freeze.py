#!/usr/bin/env python
"""
outputs the frozen packages
"""
import sys
import os
import argparse
import subprocess
parser = argparse.ArgumentParser(description=__doc__.strip())
parser.add_argument('--venv', default='requirements/temporary_venv')
parser.add_argument(
    "--template", default="requirements/template.txt",)
parser.add_argument(
    "--out", default=sys.stdout, type=argparse.FileType('w'),
    help='the file where packages should be written to')


def main(args):
    if not os.path.isdir(args.venv):
        subprocess.check_call([
            sys.executable, '-m', 'virtualenv', args.venv
        ])
    subprocess.check_call([
        os.path.join(args.venv, 'bin/pip'),
        'install', '-U', '-r', args.template])

    subprocess.check_call([
        os.path.join(args.venv, 'bin/pip'), 'freeze'
    ], stdout=args.out)


if __name__ == '__main__':
    main(parser.parse_args())
