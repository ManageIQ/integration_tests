# Acts like a normal conftest file, but should be invoked with py.test using '-p rhci'
import pytest

from rhci.robo import RoboNamespace, robo_spoofer
from utils import conf, ports
from utils.net import random_port
from utils.providers import get_mgmt
from utils.ssh import SSHClient, forward_tunnel


@pytest.fixture
def robo():
    return RoboNamespace()


@pytest.fixture(scope='session', autouse=True)
def _robo_spoofer():
    # make sure we use the spoofer early in a test session
    robo_spoofer()


def pytest_addoption(parser):
    group = parser.getgroup('rhci')
    group.addoption('--rhci-cfme-addr', default=None,
        help="CFME address on the private RHCI network, used to tunnel web UI, SSH, and DB ports")
    group.addoption('--rhci-rhevm-addr', default=None,
        help="RHEVM engine address on the private RHCI network, used to tunnel RHEVM API")


def pytest_configure(config):
    cfme_addr = config.getoption('rhci_cfme_addr', None)
    rhevm_addr = config.getoption('rhci_rhevm_addr', None)

    setup_port_forwarding(cfme_addr, rhevm_addr)


def setup_port_forwarding(cfme_addr=None, rhevm_addr=None):
    ip_address = conf.rhci.get('ip_address')
    if ip_address is None and (cfme_addr or rhevm_addr):
        raise RuntimeError('Cannot forward ports without knowing the address of the Satellite UI '
            '(ip_address in the rhci conf yaml is not set)')

    ssh_client = SSHClient(hostname=ip_address)

    # get the routable address by inspecting the SSH connection to the satellite box,
    # so we set the network configs correctly
    local_addr = ssh_client.client_address()

    # spoof cfme appliance URL, SSH, and DB, binding to all local interfaces
    if cfme_addr:
        local_https_port = random_port()
        forward_tunnel(ssh_client, ('0.0.0.0', local_https_port), (cfme_addr, 443))
        conf.runtime['env']['base_url'] = 'https://{}:{}/'.format(local_addr, local_https_port)

        local_ssh_port = random_port()
        forward_tunnel(ssh_client, ('0.0.0.0', local_ssh_port), (cfme_addr, 22))
        ports.SSH = local_ssh_port

        local_db_port = random_port()
        forward_tunnel(ssh_client, ('0.0.0.0', local_db_port), (cfme_addr, 5432))
        ports.DB = local_db_port

    # change the rhevm api url for the provider (providers are cached, so this should stick)
    if rhevm_addr:
        local_rhevm_api_port = random_port()
        forward_tunnel(ssh_client, ('0.0.0.0', local_rhevm_api_port), (rhevm_addr, 443))
        rhevm_api_url = 'https://{}:{}'.format(local_addr, local_rhevm_api_port)
        mgmt = get_mgmt('rhevm-rhci')
        # a public interface for changing the api endpoint would be nice, but for now...
        mgmt._api = None
        mgmt._api_kwargs['url'] = rhevm_api_url
