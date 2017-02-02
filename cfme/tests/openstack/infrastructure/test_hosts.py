import pytest

from cfme.configure.tasks import is_host_analysis_finished
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import InfoBlock, Quadicon, toolbar
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def test_host_configuration(provider, soft_assert):
    navigate_to(provider, 'Details')
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(is_host_analysis_finished, [host.name], delay=15,
                 timeout="10m", fail_func=toolbar.refresh)
        fields = ['Packages', 'Services', 'Files']
        for field in fields:
            value = int(host.get_detail("Configuration", field))
            soft_assert(value > 0, 'Nodes number of {} is 0'.format(field))


def test_host_cpu_resources(provider, soft_assert):
    navigate_to(provider, 'Details')
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        fields = ['Number of CPUs', 'Number of CPU Cores',
                  'CPU Cores Per Socket']
        for field in fields:
            value = int(host.get_detail("Properties", field))
            soft_assert(value > 0, "Aggregate Node {} is 0".format(field))


def test_host_devices(provider):
    navigate_to(provider, 'Details')
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        assert int(host.get_detail("Properties", "Devices")) > 0


def test_host_hostname(provider, soft_assert):
    provider.summary.relationships.nodes.click()
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        result = host.get_detail("Properties", "Hostname")
        soft_assert(result, "Missing hostname in: " + str(result))


def test_host_memory(provider):
    navigate_to(provider, 'Details')
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        result = int(host.get_detail("Properties", "Memory").split()[0])
        assert result > 0


def test_host_security(provider, soft_assert):
    navigate_to(provider, 'Details')
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        soft_assert(
            int(host.get_detail("Security", "Users")) > 0,
            'Nodes number of Users is 0')

        soft_assert(
            int(host.get_detail("Security", "Groups")) > 0,
            'Nodes number of Groups is 0')


def test_host_zones_assigned(provider):
    navigate_to(provider, 'Details')
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    my_quads = filter(lambda q: True if 'Compute' in q.name else False,
                      my_quads)
    for quad in my_quads:
        host = Host(name=quad.name)
        result = host.get_detail('Relationships', 'Availability Zone')
        assert result, "Availability zone doesn't specified"
