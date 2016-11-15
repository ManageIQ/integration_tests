from utils import testgen
from cfme.web_ui import Quadicon
from cfme.infrastructure.host import Host
import pytest

pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'], scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def test_host_hostname(provider, soft_assert):
    provider.summary.relationships.nodes.click()
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        result = host.get_detail("Properties", "Hostname")
        soft_assert(result) != '', "Missing hostname in: " + str(host)
