import pytest

from cfme.configure.tasks import is_host_analysis_finished
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import toolbar
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.fixture(scope="module")
def host_collection(appliance):
    return appliance.collections.hosts


def test_host_configuration(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        host.run_smartstate_analysis()
        wait_for(is_host_analysis_finished, [host.name], delay=15,
                 timeout="10m", fail_func=toolbar.refresh)
        fields = ['Packages', 'Services', 'Files']
        for field in fields:
            value = int(host.get_detail("Configuration", field))
            soft_assert(value > 0, 'Nodes number of {} is 0'.format(field))


def test_host_cpu_resources(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        fields = ['Number of CPUs', 'Number of CPU Cores',
                  'CPU Cores Per Socket']
        for field in fields:
            value = int(host.get_detail("Properties", field))
            soft_assert(value > 0, "Aggregate Node {} is 0".format(field))


def test_host_auth(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        navigate_to(host, 'Details')
        auth_status = host.get_detail('Authentication Status', 'SSH Key Pair Credentials')
        soft_assert(auth_status == 'Valid',
                    'Incorrect SSH authentication status {}'.format(auth_status))


def test_host_devices(host_collection, provider):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        assert int(host.get_detail("Properties", "Devices")) > 0


def test_host_hostname(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        result = host.get_detail("Properties", "Hostname")
        soft_assert(result, "Missing hostname in: " + str(result))


def test_host_memory(host_collection, provider):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        result = int(host.get_detail("Properties", "Memory").split()[0])
        assert result > 0


def test_host_security(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        soft_assert(
            int(host.get_detail("Security", "Users")) > 0,
            'Nodes number of Users is 0')

        soft_assert(
            int(host.get_detail("Security", "Groups")) > 0,
            'Nodes number of Groups is 0')


def test_host_smbios_data(host_collection, provider, soft_assert):
    """Checks that Manufacturer/Model values are shown for each infra node"""
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        navigate_to(host, 'Details')
        res = host.get_detail('Properties', 'Manufacturer / Model')
        soft_assert(res, 'Manufacturer / Model value are empty')
        soft_assert(res != 'N/A')


def test_host_zones_assigned(host_collection, provider):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        result = host.get_detail('Relationships', 'Availability Zone')
        assert result, "Availability zone doesn't specified"
