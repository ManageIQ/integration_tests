#!/usr/bin/env python3
import argparse
import sys

import freeze

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
HERE = Path(__file__).resolve().parent

# fmt: off
RUNS = [
    ("template_docs.txt", "frozen_docs.txt"),
    ("template.txt", "frozen.txt"),
]
# fmt: on

parser = argparse.ArgumentParser()
parser.add_argument(
    "--upgrade-only", default=None, help="updates only the given package instead of all of them"
)

# todo loop over pythons here and disallow virtualenv


def main(conf):

    """
    this one simply runs the freezing for all templates

    this is the one you should always use
    """
    with freeze.maybe_transient_venv_dir(None, False) as venv:
        for template, out in RUNS:
            out = out.replace(".txt", ".py{major}.txt".format(major=sys.version_info[0]))
            args = argparse.Namespace(
                venv=venv,
                keep=True,
                template=str(HERE.joinpath(template)),
                out=str(HERE.joinpath(out)),
                upgrade_only=conf.upgrade_only,
            )
            freeze.main(args)


if __name__ == "__main__":
    main(parser.parse_args())
