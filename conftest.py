"""
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
"""
from pkgutil import iter_modules

import pytest
import requests

from fixtures.artifactor_plugin import art_client, appliance_ip_address
from cfme.fixtures.rdb import Rdb
from fixtures.pytest_store import store
from utils import ports
from utils.conf import rdb
from utils.log import logger
from utils.path import data_path
from utils.net import net_check
from utils.wait import TimedOutError


class _AppliancePoliceException(Exception):
    def __init__(self, message, port, *args, **kwargs):
        super(_AppliancePoliceException, self).__init__(message, port, *args, **kwargs)
        self.message = message
        self.port = port

    def __str__(self):
        return "{} (port {})".format(self.message, self.port)


@pytest.mark.tryfirst
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme', 'cfme: options related to cfme/miq appliances')
    # Keeping due to compatibility
    parser.addoption("--no-tracer", dest="no_tracer", action="store_true", default=False,
                     help="Disable the function tracer (REMOVED, doesn't do anything!)")
    parser.addoption("--tracer", dest="tracer", action="store_true", default=False,
                     help="Enable the function tracer (REMOVED, doesn't do anything!)")


def pytest_cmdline_main(config):
    for opt in ['--tracer', '--no-tracer']:
        if config.getoption(opt):
            print("The {} option has been REMOVED, it doesn't do anything; please, stop using it!"
                  .format(opt))


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
                raise _AppliancePoliceException('Unable to connect', port_numbers[port])

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
        e_message = str(e)
    except Exception as e:
        e_message = str(e)

    # Regardles of the exception raised, we didn't return anywhere above
    # time to call a human
    msg = 'Help! My appliance {} crashed with: {}'.format(store.current_appliance.url, e_message)
    store.slave_manager.message(msg)
    if 'appliance_police_recipients' in rdb:
        rdb_kwargs = {
            'subject': 'RDB Breakpoint: Appliance failure',
            'recipients': rdb.appliance_police_recipients,
        }
    else:
        rdb_kwargs = {}
    Rdb(msg).set_trace(**rdb_kwargs)
    store.slave_manager.message('Resuming testing following remote debugging')


def _pytest_plugins_generator(*extension_pkgs):
    # Finds all submodules in pytest extension packages and loads them
    for extension_pkg in extension_pkgs:
        path = extension_pkg.__path__
        prefix = '%s.' % extension_pkg.__name__
        for importer, modname, is_package in iter_modules(path, prefix):
            yield modname

pytest_plugins = (

    'fixtures.pytest_store',

    'fixtures.portset',
    'fixtures.artifactor_plugin',
    'fixtures.parallelizer',

    'fixtures.single_appliance_sprout',
    'fixtures.dev_branch',
    'fixtures.events',
    'fixtures.appliance_update',
    'fixtures.blockers',
    'fixtures.browser',
    'fixtures.cfme_data',
    'fixtures.datafile',
    'fixtures.db',
    'fixtures.fixtureconf',
    'fixtures.log',
    'fixtures.maximized',
    'fixtures.merkyl',
    'fixtures.mgmt_system',
    'fixtures.nelson',
    'fixtures.node_annotate',
    'fixtures.page_screenshots',
    'fixtures.perf',
    'fixtures.prov_filter',
    'fixtures.provider',
    'fixtures.qa_contact',
    'fixtures.randomness',
    'fixtures.rbac',
    'fixtures.screenshots',
    'fixtures.snmp',
    'fixtures.soft_assert',
    'fixtures.ssh_client',
    'fixtures.templateloader',
    'fixtures.terminalreporter',
    'fixtures.ui_coverage',
    'fixtures.version_file',
    'fixtures.video',
    'fixtures.virtual_machine',
    'fixtures.widgets',

    'markers',

    'cfme.fixtures.pytest_selenium',
    'cfme.fixtures.configure_auth_mode',
    'cfme.fixtures.rdb',
    'cfme.fixtures.rest_api',
    'cfme.fixtures.service_fixtures',
    'cfme.fixtures.smtp',
    'cfme.fixtures.tag',
    'cfme.fixtures.vm_name',

    'metaplugins',
)
collect_ignore = ["tests/scenarios"]
