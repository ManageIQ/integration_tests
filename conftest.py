"""
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
"""
from pkgutil import iter_modules

import pytest
from scp import SCPException

import cfme.fixtures
import fixtures
import markers
import metaplugins
from fixtures.pytest_store import store
from utils.log import logger


@pytest.mark.tryfirst
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme', 'cfme: options related to cfme/miq appliances')
    parser.addoption("--use-provider", action="append", default=[],
        help="list of providers or tags to include in test")


@pytest.fixture(scope="session", autouse=True)
def set_session_timeout():
    vmdb_config = store.current_appliance.get_yaml_config("vmdb")
    if vmdb_config["session"]["timeout"] < 86400:
        vmdb_config["session"]["timeout"] = 86400
        try:
            store.current_appliance.set_yaml_config("vmdb", vmdb_config)
        except SCPException as ex:
            logger.error('Setting session timout failed')
            logger.error(ex)


def _pytest_plugins_generator(*extension_pkgs):
    # Finds all submodules in pytest extension packages and loads them
    for extension_pkg in extension_pkgs:
        path = extension_pkg.__path__
        prefix = '%s.' % extension_pkg.__name__
        for importer, modname, is_package in iter_modules(path, prefix):
            yield modname

pytest_plugins = tuple(_pytest_plugins_generator(fixtures, markers, cfme.fixtures, metaplugins))
collect_ignore = ["tests/scenarios"]
