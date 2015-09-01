# Acts like a normal conftest file, but should be invoked with py.test using '-p rhci'
import pytest

from rhci.robo import RoboNamespace, robo_spoofer
from utils import conf


@pytest.fixture
def robo():
    return RoboNamespace()


@pytest.fixture(scope='session', autouse=True)
def _robo_spoofer():
    # make sure we use the spoofer early in a test session
    robo_spoofer()


def pytest_addoption(parser):
    group = parser.getgroup('rhci')
    group.addoption('--inject-rhci-credentials', dest='inject_rhci_creds', action='store_true',
        default=False, help="Inject credentials from the credentials_rhci conf into credentials")


def pytest_configure(config):
    if config.getoption('inject_rhci_creds'):
        conf.runtime['credentials'].update(conf.credentials_rhci)
