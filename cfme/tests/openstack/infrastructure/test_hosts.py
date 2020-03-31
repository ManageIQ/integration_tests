import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenstackInfraProvider], scope='module'),
]

VIEWS = ["List View", "Tile View"]


@pytest.fixture(scope="module")
def host_collection(appliance):
    return appliance.collections.hosts


@pytest.mark.regression
def test_host_configuration(host_collection, provider, soft_assert, appliance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        host.run_smartstate_analysis()
        task = appliance.collections.tasks.instantiate(
            name=f"SmartState Analysis for '{host.name}'", tab='MyOtherTasks')
        task.wait_for_finished()
        fields = ['Packages', 'Services', 'Files']
        view = navigate_to(host, 'Details')
        for field in fields:
            value = int(view.entities.summary('Configuration').get_text_of(field))
            soft_assert(value > 0, f'Nodes number of {field} is 0')


@pytest.mark.regression
def test_host_cpu_resources(host_collection, provider, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        fields = ['Number of CPUs', 'Number of CPU Cores',
                  'CPU Cores Per Socket']
        view = navigate_to(host, 'Details')
        for field in fields:
            value = int(view.entities.summary('Properties').get_text_of(field))
            soft_assert(value > 0, f"Aggregate Node {field} is 0")


@pytest.mark.regression
def test_host_auth(host_collection, provider, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        auth_status = view.entities.summary('Authentication Status').get_text_of(
            'SSH Key Pair Credentials')
        soft_assert(auth_status == 'Valid',
                    f'Incorrect SSH authentication status {auth_status}')


@pytest.mark.regression
def test_host_devices(host_collection, provider):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = int(view.entities.summary('Properties').get_text_of('Devices').split()[0])
        assert result > 0


@pytest.mark.regression
def test_host_hostname(host_collection, provider, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = view.entities.summary('Properties').get_text_of('Hostname')
        soft_assert(result, "Missing hostname in: " + str(result))


@pytest.mark.regression
def test_host_memory(host_collection, provider):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = int(view.entities.summary('Properties').get_text_of('Memory').split()[0])
        assert result > 0


@pytest.mark.regression
def test_host_security(host_collection, provider, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        soft_assert(
            int(view.entities.summary('Security').get_text_of('Users')) > 0,
            'Nodes number of Users is 0')

        soft_assert(
            int(view.entities.summary('Security').get_text_of('Groups')) > 0,
            'Nodes number of Groups is 0')


@pytest.mark.regression
def test_host_smbios_data(host_collection, provider, soft_assert):
    """Checks that Manufacturer/Model values are shown for each infra node

    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        res = view.entities.summary('Properties').get_text_of('Manufacturer / Model')
        soft_assert(res, 'Manufacturer / Model value are empty')
        soft_assert(res != 'N/A')


@pytest.mark.regression
def test_host_zones_assigned(host_collection, provider):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    assert hosts
    for host in hosts:
        view = navigate_to(host, 'Details')
        result = view.entities.summary('Relationships').get_text_of('Availability Zone')
        assert result, "Availability zone doesn't specified"


@pytest.mark.rfe
def test_hypervisor_hostname(host_collection, provider, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hvisors = provider.mgmt.list_host()
    hosts = host_collection.all()
    for host in hosts:
        view = navigate_to(host, 'Details')
        hv_name = view.entities.summary('Properties').get_text_of('Hypervisor Hostname')
        soft_assert(hv_name in hvisors,
            f"Hypervisor hostname {hv_name} is not in Hypervisor list")


@pytest.mark.rfe
@pytest.mark.parametrize("view_type", VIEWS)
def test_hypervisor_hostname_views(host_collection, provider, view_type, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hvisors = provider.mgmt.list_host()
    view = navigate_to(host_collection, 'All')
    view.toolbar.view_selector.select(view_type)
    items = view.entities.get_all()
    for item in items:
        hv_name = item.data['hypervisor_hostname']
        soft_assert(hv_name in hvisors,
                    f"Hypervisor hostname {hv_name} is not in Hypervisor list")


@pytest.mark.rfe
def test_host_networks(provider, host_collection, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()
    nodes = provider.mgmt.nodes
    networks = {node.name: provider.mgmt.api.servers.ips(server=node) for node in nodes}

    for host in hosts:
        view = navigate_to(host, 'Details')
        cloud_net = view.entities.summary('Relationships').get_text_of('Cloud Networks')
        host_name = view.entities.summary('Properties').get_text_of('Hypervisor Hostname')

        soft_assert(int(cloud_net) == len(networks[host_name]),
                    "Networks associated to host does not match between UI and OSP")


@pytest.mark.rfe
def test_host_subnets(provider, appliance, host_collection, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    hosts = host_collection.all()

    for host in hosts:
        view = navigate_to(host, 'Details')
        cloud_subnet = view.entities.summary('Relationships').get_text_of('Cloud Subnets')
        view = navigate_to(host, 'Subnets')
        soft_assert(int(cloud_subnet) == view.entities.paginator.items_amount,
                    "Subnets associated to host does not match")
