import pytest
import re

from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.cluster import Cluster
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import InfoBlock, Quadicon
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.uncollectif(lambda: current_version() < '5.7'),
              pytest.mark.usefixtures("setup_provider_modscope")]


ROLES = ['NovaCompute', 'Controller', 'Compute', 'BlockStorage', 'SwiftStorage',
         'CephStorage']


def test_host_role_type(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        role_name = str(quad.name)
        role_name = re.search(r'\((\w+)\)', role_name).group(1)
        assert role_name in ROLES


def test_roles_name(provider):
    navigate_to(Cluster, 'All')
    my_roles_quads = list(Quadicon.all())
    for quad in my_roles_quads:
        role_name = str(quad.name).split('-')[1]
        assert role_name in ROLES
