"""
Top-level conftest.py does a couple of things:

1) Add cfme_pages repo to the sys.path automatically
2) Load a number of plugins and fixtures automatically
"""
from pkgutil import iter_modules

import pytest
import requests
from Runner import Run

import cfme.fixtures
import fixtures
import markers
import metaplugins
from cfme.fixtures.rdb import Rdb
from fixtures.pytest_store import store
from utils import local_vpn
from utils.log import logger
from utils.net import net_check
from utils.path import data_path
from utils.ssh import SSHClient
from utils.version import current_version


@pytest.mark.hookwrapper
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme', 'cfme: options related to cfme/miq appliances')
    yield


@pytest.fixture(scope="session", autouse=True)
def set_session_timeout():
    try:
        vmdb_config = store.current_appliance.get_yaml_config("vmdb")
        if vmdb_config["session"]["timeout"] < 86400:
            vmdb_config["session"]["timeout"] = 86400
            store.current_appliance.set_yaml_config("vmdb", vmdb_config)
    except Exception as ex:
        # Definitely need to implement retries or something, this is
        # just a bandaid
        logger.error('Setting session timout failed')
        logger.exception(ex)


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


@pytest.fixture(autouse=True, scope="function")
def appliance_police():
    if not store.slave_manager:
        return
    try:
        ports = {'ssh': 22, 'https': 443, 'postgres': 5432}
        port_results = {pn: net_check(pp) for pn, pp in ports.items()}
        for port, result in port_results.items():
            if not result:
                raise Exception('Port {} was not contactable'.format(port))
        status_code = requests.get(store.current_appliance.url, verify=False,
                                   timeout=60).status_code
        if status_code != 200:
            raise Exception('Status code was {}, should be 200'.format(status_code))
    except Exception as e:
        store.slave_manager.message(
            'Help! My appliance {} crashed with: {}'.format(
                store.current_appliance.url,
                e.message))
        Rdb().set_trace(**{
            'subject': 'RDB Breakpoint: Appliance failure',
            'recipients': ['semyers@redhat.com', 'psavage@redhat.com'],
        })
        store.slave_manager.message('Resuming testing following remote debugging')


@pytest.yield_fixture(autouse=True, scope="module")
def provider_vpn_setup_moduledb():
    data = {}
    yield data
    for key, crud in data.iteritems():
        if crud.exists:
            crud.delete(cancel=False)
        appliance = fixtures.pytest_store.store.current_appliance
        appliance.remove_openvpn()  # Just the config, the package itself stays


@pytest.yield_fixture(autouse=True, scope="function")
def provider_vpn_setup(request, provider_vpn_setup_moduledb):
    if "provider_crud" not in request.fixturenames:
        yield
    else:
        crud = request.getfuncargvalue("provider_crud")
        if crud.key in provider_vpn_setup_moduledb:
            yield
        else:
            data = crud.get_yaml_data()
            if "vpn" not in data:
                yield
            else:
                if not Run.command("sudo -n true"):
                    pytest.skip("The environment does not allow non-password sudo.")
                else:
                    fixtures.pytest_store.store.current_appliance.setup_openvpn_for(crud.key)
                    fixtures.pytest_store.store.current_appliance.uninstall_epel()
                    provider_vpn_setup_moduledb[crud.key] = crud
                    with local_vpn.vpn_for(crud.key):
                        yield


def _pytest_plugins_generator(*extension_pkgs):
    # Finds all submodules in pytest extension packages and loads them
    for extension_pkg in extension_pkgs:
        path = extension_pkg.__path__
        prefix = '%s.' % extension_pkg.__name__
        for importer, modname, is_package in iter_modules(path, prefix):
            yield modname

pytest_plugins = tuple(_pytest_plugins_generator(fixtures, markers, cfme.fixtures, metaplugins))
collect_ignore = ["tests/scenarios"]
