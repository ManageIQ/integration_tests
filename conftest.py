'''
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
'''
from pkgutil import iter_modules

import pytest

# From cfme_tests
import fixtures, markers

# From cfme_pages
import plugin

def _pytest_plugins_generator(*extension_pkgs):
    # Finds all submodules in pytest extension packages and loads them
    for extension_pkg in extension_pkgs:
        path = extension_pkg.__path__
        prefix = '%s.' % extension_pkg.__name__
        for importer, modname, is_package in iter_modules(path, prefix):
            if not is_package:
                yield modname

pytest_plugins = tuple(_pytest_plugins_generator(fixtures, markers, plugin))

collect_ignore = ["tests/scenarios"]
