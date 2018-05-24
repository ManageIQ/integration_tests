import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenstackInfraProvider], scope='module'),
]


@pytest.fixture(scope="module")
def host_collection(appliance):
    return appliance.collections.hosts


def test_host_configuration(host_collection, provider, soft_assert, appliance):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        host.run_smartstate_analysis()
        task = appliance.collections.tasks.instantiate(
            name="SmartState Analysis for '{}'".format(host.name), tab='MyOtherTasks')
        task.wait_for_finished()
        fields = ['Packages', 'Services', 'Files']
        view = navigate_to(host, 'Details')
        for field in fields:
            value = int(view.entities.summary('Configuration').get_text_of(field))
            soft_assert(value > 0, 'Nodes number of {} is 0'.format(field))


def test_host_cpu_resources(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        fields = ['Number of CPUs', 'Number of CPU Cores',
                  'CPU Cores Per Socket']
        view = navigate_to(host, 'Details')
        for field in fields:
            value = int(view.entities.summary('Properties').get_text_of(field))
            soft_assert(value > 0, "Aggregate Node {} is 0".format(field))


def test_host_auth(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        auth_status = view.entities.summary('Authentication Status').get_text_of(
            'SSH Key Pair Credentials')
        soft_assert(auth_status == 'Valid',
                    'Incorrect SSH authentication status {}'.format(auth_status))


def test_host_devices(host_collection, provider):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = int(view.entities.summary('Properties').get_text_of('Devices').split()[0])
        assert result > 0


def test_host_hostname(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = view.entities.summary('Properties').get_text_of('Hostname')
        soft_assert(result, "Missing hostname in: " + str(result))


def test_host_memory(host_collection, provider):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = int(view.entities.summary('Properties').get_text_of('Memory').split()[0])
        assert result > 0


def test_host_security(host_collection, provider, soft_assert):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        soft_assert(
            int(view.entities.summary('Security').get_text_of('Users')) > 0,
            'Nodes number of Users is 0')

        soft_assert(
            int(view.entities.summary('Security').get_text_of('Groups')) > 0,
            'Nodes number of Groups is 0')


def test_host_smbios_data(host_collection, provider, soft_assert):
    """Checks that Manufacturer/Model values are shown for each infra node"""
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        res = view.entities.summary('Properties').get_text_of('Manufacturer / Model')
        soft_assert(res, 'Manufacturer / Model value are empty')
        soft_assert(res != 'N/A')


def test_host_zones_assigned(host_collection, provider):
    hosts = host_collection.all(provider)
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = view.entities.summary('Relationships').get_text_of('Availability Zone')
        assert result, "Availability zone doesn't specified"
