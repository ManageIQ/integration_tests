"""
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
"""
from pkgutil import iter_modules

import pytest
import requests

import cfme.fixtures
import fixtures
import markers
import metaplugins
from fixtures.artifactor_plugin import art_client, appliance_ip_address
from cfme.fixtures.rdb import Rdb
from fixtures.pytest_store import store
from utils import ports
from utils.log import logger
from utils.path import data_path
from utils.net import net_check
from utils.wait import TimedOutError


class _AppliancePoliceException(Exception):
    def __init__(self, message, port, *args, **kwargs):
        super(_AppliancePoliceException, self).__init__(message, port, *args, **kwargs)
        self.message = message
        self.port = port


@pytest.mark.hookwrapper
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme', 'cfme: options related to cfme/miq appliances')
    yield


@pytest.fixture(scope="session", autouse=True)
def set_session_timeout():
    store.current_appliance.set_session_timeout(86400)


@pytest.fixture(scope="session", autouse=True)
def fix_merkyl_workaround():
    """Workaround around merkyl not opening an iptables port for communication"""
    ssh_client = store.current_appliance.ssh_client
    if ssh_client.run_command('test -s /etc/init.d/merkyl').rc != 0:
        logger.info('Rudely overwriting merkyl init.d on appliance;')
        local_file = data_path.join("bundles").join("merkyl").join("merkyl")
        remote_file = "/etc/init.d/merkyl"
        ssh_client.put_file(local_file.strpath, remote_file)
        ssh_client.run_command("service merkyl restart")
        art_client.fire_hook('setup_merkyl', ip=appliance_ip_address)


@pytest.fixture(scope="session", autouse=True)
def fix_missing_hostname():
    """Fix for hostname missing from the /etc/hosts file

    Note: Affects RHOS-based appliances but can't hurt the others so
          it's applied on all.
    """
    ssh_client = store.current_appliance.ssh_client
    logger.info("Checking appliance's /etc/hosts for its own hostname")
    if ssh_client.run_command('grep $(hostname) /etc/hosts').rc != 0:
        logger.info("Adding it's hostname to its /etc/hosts")
        # Append hostname to the first line (127.0.0.1)
        ret = ssh_client.run_command('sed -i "1 s/$/ $(hostname)/" /etc/hosts')
        if ret.rc == 0:
            logger.info("Hostname added")
        else:
            logger.error("Failed to add hostname")


@pytest.fixture(autouse=True, scope="function")
def appliance_police():
    if not store.slave_manager:
        return
    try:
        port_numbers = {
            'ssh': ports.SSH,
            'https': store.current_appliance.ui_port,
            'postgres': ports.DB}
        port_results = {pn: net_check(pp, force=True) for pn, pp in port_numbers.items()}
        for port, result in port_results.items():
            if not result:
                raise _AppliancePoliceException('Port {} was not contactable'.format(port),
                    port_numbers[port])

        try:
            status_code = requests.get(store.current_appliance.url, verify=False,
                                       timeout=120).status_code
        except Exception:
            raise _AppliancePoliceException('Getting status code failed', port_numbers['https'])

        if status_code != 200:
            raise _AppliancePoliceException('Status code was {}, should be 200'.format(
                status_code), port_numbers['https'])
        return
    except _AppliancePoliceException as e:
        # special handling for known failure conditions
        if e.port == 443:
            # Lots of rdbs lately where evm seems to have entirely crashed
            # and (sadly) the only fix is a rude restart
            store.current_appliance.restart_evm_service(rude=True)
            try:
                store.current_appliance.wait_for_web_ui(900)
                store.write_line('EVM was frozen and had to be restarted.', purple=True)
                return
            except TimedOutError:
                pass
        e_message = e.message
    except Exception as e:
        e_message = e.args[0]

    # Regardles of the exception raised, we didn't return anywhere above
    # time to call a human
    msg = 'Help! My appliance {} crashed with: {}'.format(store.current_appliance.url, e_message)
    store.slave_manager.message(msg)
    Rdb(msg).set_trace(**{
        'subject': 'RDB Breakpoint: Appliance failure',
        'recipients': ['semyers@redhat.com', 'psavage@redhat.com'],
    })
    store.slave_manager.message('Resuming testing following remote debugging')


def _pytest_plugins_generator(*extension_pkgs):
    # Finds all submodules in pytest extension packages and loads them
    for extension_pkg in extension_pkgs:
        path = extension_pkg.__path__
        prefix = '%s.' % extension_pkg.__name__
        for importer, modname, is_package in iter_modules(path, prefix):
            yield modname

pytest_plugins = tuple(_pytest_plugins_generator(fixtures, markers, cfme.fixtures, metaplugins))
collect_ignore = ["tests/scenarios"]
