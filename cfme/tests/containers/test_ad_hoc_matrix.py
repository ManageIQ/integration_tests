import pytest
import re
from cfme.containers.provider import ContainersProvider
from utils import testgen
from utils import conf
from utils.ssh import SSHClient
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.mark.polarion('CMP-10643'):
def test_basic_metrics(provider):
    pass
