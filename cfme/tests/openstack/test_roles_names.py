
import pytest

from cfme.web_ui import Quadicon
from cfme.infrastructure.cluster import Cluster

from utils import testgen
from utils.appliance.endpoints.ui import navigate_to


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')

ROLES = ['Compute', 'Controller', 'BlockStorage', 'SwiftStorage',
         'CephStorage']


@pytest.mark.usefixtures("setup_provider_modscope")
def test_roles_name(provider):
    navigate_to(Cluster, 'All')
    my_roles_quads = list(Quadicon.all())
    result = True
    while result:
        for quad in my_roles_quads:
            role_name = str(quad.name).split('-')[1]
            if role_name not in ROLES:
                result = False
    assert result
