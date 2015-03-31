"""
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
"""
from pkgutil import iter_modules
from subprocess import Popen, PIPE

import pytest
import re

import cfme.fixtures
import fixtures
import markers
import metaplugins
from fixtures.pytest_store import store
from utils.log import logger
from utils.path import data_path
from utils.ssh import SSHClient
from utils.version import current_version


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
        store.current_appliance.set_yaml_config("vmdb", vmdb_config)


@pytest.fixture(scope="session", autouse=True)
def set_default_domain():
    if current_version() < "5.3":
        return  # Domains are not in 5.2.x and lower
    ssh_client = SSHClient()
    # The command ignores the case when the Default domain is not present (: true)
    result = ssh_client.run_rails_command(
        "\"d = MiqAeDomain.where :name => 'Default'; puts (d) ? d.first.enabled : true\"")
    if result.output.lower().strip() != "true":
        # Re-enable the domain
        ssh_client.run_rails_command(
            "\"d = MiqAeDomain.where :name => 'Default'; d = d.first; d.enabled = true; d.save!\"")


@pytest.fixture(scope="session", autouse=True)
def fix_merkyl_workaround():
    """Workaround around merkyl not opening an iptables port for communication"""
    ssh_client = SSHClient()
    if ssh_client.run_command('test -f /etc/init.d/merkyl').rc == 0:
        logger.info('Rudely overwriting merkyl init.d on appliance;')
        local_file = data_path.join("bundles").join("merkyl").join("merkyl")
        remote_file = "/etc/init.d/merkyl"
        ssh_client.put_file(local_file.strpath, remote_file)
        ssh_client.run_command("service merkyl restart")


def _pytest_plugins_generator(*extension_pkgs):
    # Finds all submodules in pytest extension packages and loads them
    for extension_pkg in extension_pkgs:
        path = extension_pkg.__path__
        prefix = '%s.' % extension_pkg.__name__
        for importer, modname, is_package in iter_modules(path, prefix):
            yield modname

pytest_plugins = tuple(_pytest_plugins_generator(fixtures, markers, cfme.fixtures, metaplugins))
collect_ignore = ["tests/scenarios"]
