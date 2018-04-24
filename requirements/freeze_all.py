#!/usr/bin/env python
import argparse
import sys

import freeze

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
HERE = Path(__file__).resolve().parent

RUNS = [
    ('template_docs.txt', 'frozen_docs.txt'),
    ('template.txt', 'frozen.txt'),
]


def main():
    """
    this one simply runs the freezing for all templates

    this is the one you should always use
    """
    with freeze.maybe_transient_venv_dir(None, False) as venv:
        for template, out in RUNS:
            out = out.replace('.txt', '.py{major}.txt'.format(major=sys.version_info[0]))
            args = argparse.Namespace(
                venv=venv,
                keep=True,
                template=str(HERE.joinpath(template)),
                out=str(HERE.joinpath(out))
            )
            freeze.main(args)


if __name__ == "__main__":
    main()
