import pytest
from utils import testgen
from cfme.web_ui import Quadicon
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel

pytest_generate_tests = testgen.generate([OpenstackInfraProvider], scope='module')


def get_integer_value(x):
    return int(x.split(' ')[0])


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_cpu_resources(provider, soft_assert):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        soft_assert(get_integer_value(host.get_detail("Properties",
                                                      "Number of CPUs")) > 0,
                    "Aggregate Node CPU resources is 0")
        soft_assert(get_integer_value(
            host.get_detail("Properties", "Number of CPU Cores")) > 0,
            "Aggregate node CPUs is 0")
        soft_assert(get_integer_value(
            host.get_detail("Properties", "CPU Cores Per Socket")) > 0,
            "Aggregate Node CPU Cores is 0")
