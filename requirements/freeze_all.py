#!/usr/bin/env python
import freeze
import argparse
import pathlib2
HERE = pathlib2.Path(__file__).resolve().parent
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
            args = argparse.Namespace(
                venv=venv,
                keep=True,
                template=str(HERE.joinpath(template)),
                out=str(HERE.joinpath(out))
            )
            freeze.main(args)


if __name__ == "__main__":
    main()
