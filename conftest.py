"""
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
"""
from pkgutil import iter_modules

import cfme.fixtures

# From cfme_tests
import fixtures
import markers


def _pytest_plugins_generator(*extension_pkgs):
    # Finds all submodules in pytest extension packages and loads them
    for extension_pkg in extension_pkgs:
        path = extension_pkg.__path__
        prefix = '%s.' % extension_pkg.__name__
        for importer, modname, is_package in iter_modules(path, prefix):
            if not is_package:
                yield modname


def pytest_addoption(parser):
    parser.addoption("--use-provider", action="append", default=[],
        help="list of providers or tags to include in test")

pytest_plugins = tuple(_pytest_plugins_generator(fixtures, markers, cfme.fixtures))
collect_ignore = ["tests/scenarios"]
