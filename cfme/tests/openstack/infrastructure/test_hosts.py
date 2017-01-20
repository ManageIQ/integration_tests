import pytest
from utils import testgen
from cfme.web_ui import Quadicon, toolbar
from cfme.infrastructure.host import Host
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel
from cfme.configure.tasks import is_host_analysis_finished
from utils.wait import wait_for


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


ROLES = ['NovaCompute', 'Controller', 'BlockStorage', 'SwiftStorage',
         'CephStorage']


def test_host_configuration(provider, soft_assert):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(lambda: is_host_analysis_finished(host.name), delay=15,
                 timeout="10m", fail_func=lambda: toolbar.select('Reload'))
        soft_assert(
            int(host.get_detail("Configuration", "Packages")) > 0,
            'Nodes number of Packages is 0')

        soft_assert(
            int(host.get_detail("Configuration", "Services")) > 0,
            'Nodes number of Services is 0')

        soft_assert(int(host.get_detail("Configuration", "Files")) > 0,
                    'Nodes number of Files is 0')


def test_host_cpu_resources(provider, soft_assert):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        soft_assert(host.get_detail("Properties", "Number of CPUs") > 0,
                    "Aggregate Node CPU resources is 0")
        soft_assert(host.get_detail("Properties", "Number of CPU Cores") > 0,
                    "Aggregate node CPUs is 0")
        soft_assert(host.get_detail("Properties", "CPU Cores Per Socket") > 0,
                    "Aggregate Node CPU Cores is 0")


def test_host_devices(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        assert host.get_detail("Properties", "Devices") > 0


def test_host_hostname(provider, soft_assert):
    provider.summary.relationships.nodes.click()
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        result = host.get_detail("Properties", "Hostname")
        soft_assert(result) != '', "Missing hostname in: " + str(host)


def test_smbios_data(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        result = host.get_detail("Properties", "Memory")
        assert result > 0


def test_host_security(provider, soft_assert):
    provider.load_details()
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
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    my_quads = filter(lambda q: True if q.name == 'Compute' else False,
                      my_quads)
    for quad in my_quads:
        host = Host(name=quad.name)
        result = host.get_detail('Relationships', 'Availability Zone')
        assert result == 'nova'
