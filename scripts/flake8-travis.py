"""Flake8 wrapper script for Travis CI

Runs the flake8 git hook using the .flake8.conf in the root of this repository.
Assumes that python is called from the root of this repository.

"""
from flake8 import hooks

hooks.DEFAULT_CONFIG = '.flake8.conf'

if __name__ == '__main__':
    sys.exit(git_hook())
