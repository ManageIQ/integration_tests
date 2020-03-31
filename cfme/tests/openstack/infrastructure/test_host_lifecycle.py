import pytest

from cfme.exceptions import ItemNotFound
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenstackInfraProvider], scope='module')
]


@pytest.fixture(scope='module')
def host(provider):
    # TODO: Implement .filter() for OpenstackNode with all()
    """Find a host for test scenario"""
    host_collection = provider.appliance.collections.openstack_nodes
    hosts = host_collection.all(provider)
    # Find a compute host with no instances on it
    for host in hosts:
        view = navigate_to(host, 'Details')
        vms = int(view.entities.summary('Relationships').get_text_of('VMs'))
        if 'Compute' in host.name and vms == 0:
            return host
    raise ItemNotFound('There is no proper host for tests')


@pytest.fixture(scope='module')
def has_mistral_service(provider):
    """Skip test if there is no Mistral service on OSPd provider"""
    services = provider.mgmt.kapi.services.list()
    if 'mistral' not in [s.name for s in services]:
        pytest.skip('Skipping because no Mistral service found on OSPD deployment')


@pytest.mark.regression
def test_scale_provider_down(provider, host, has_mistral_service):
    """Scale down Openstack Infrastructure provider
    Metadata:
        test_flag: openstack_scale

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    host.toggle_maintenance_mode()
    host_uuid = host.name.split()[0]  # cut off deployment role part from host's name
    wait_for(lambda: provider.mgmt.iapi.node.get(host_uuid).maintenance, timeout=600, delay=5)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    view = navigate_to(host, 'Details')
    wait_for(
        lambda: view.entities.summary('Properties').get_text_of('Maintenance Mode') ==
        'Enabled', delay=15, timeout=300,
        message=f"Maintenance Mode of host {host.name} becomes Enabled",
        fail_func=host.browser.refresh)
    assert view.entities.summary('Properties').get_text_of('Maintenance Mode') == 'Enabled'
    provider.scale_down()
    wait_for(lambda: provider.mgmt.iapi.node.get(host_uuid).provision_state == 'available', delay=5,
             timeout=1200)
    host.name = host_uuid  # host's name is changed after scale down
    host.browser.refresh()
    wait_for(lambda: host.exists, delay=15, timeout=600,
             message=f"Hostname changed to {host.name} after scale down",
             fail_func=provider.browser.refresh)
    view = navigate_to(host, 'Details')
    wait_for(
        lambda: view.entities.summary('Openstack Hardware').get_text_of('Provisioning State') ==
        'available', delay=15, timeout=600,
        message=f"Provisioning State of host {host.name} is available",
        fail_func=host.browser.refresh)
    prov_state = view.entities.summary('Openstack Hardware').get_text_of('Provisioning State')
    assert prov_state == 'available'


@pytest.mark.regression
def test_delete_host(appliance, host, provider, has_mistral_service):
    """Remove host from appliance and Ironic service
    Metadata:
        test_flag: openstack_scale

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    def is_host_disappeared():
        return host.name not in [h.uuid for h in provider.mgmt.iapi.node.list()]

    host.delete(cancel=False)
    wait_for(is_host_disappeared, timeout=300, delay=5)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    host_collection = appliance.collections.hosts
    assert host.name not in host_collection.all(provider)


@pytest.mark.regression
def test_register_host(provider, host, has_mistral_service):
    """Register new host by uploading instackenv.json file
    Metadata:
        test_flag: openstack_scale

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    hosts_before = [h.uuid for h in provider.mgmt.iapi.node.list()]
    provider.register(provider.data['instackenv_file_path'])
    # Wait for a new host to appear
    wait_for(lambda: len(provider.mgmt.iapi.node.list()) == len(hosts_before) + 1, timeout=300,
             delay=5)
    hosts_after = [h.uuid for h in provider.mgmt.iapi.node.list()]
    # Look for a UUID of newly created host
    for h in hosts_after:
        if h not in hosts_before:
            host.name = h
    provider.browser.refresh()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    wait_for(lambda: host.exists, delay=15, timeout=600,
             message=f"Host {host.name} become visible",
             fail_func=host.browser.refresh)

    assert host.exists


@pytest.mark.regression
def test_introspect_host(host, provider, has_mistral_service):
    """Introspect host
    Metadata:
        test_flag: openstack_scale

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    host.run_introspection()
    wait_for(lambda: provider.mgmt.iapi.node.get(host.name).inspection_finished_at, delay=15,
             timeout=600)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    view = navigate_to(host, 'Details')
    wait_for(
        lambda: view.entities.summary('Openstack Hardware').get_text_of('Introspected') ==
        'true', delay=15, timeout=600, fail_func=host.browser.refresh,
        message=f"Introspected state of host {host.name} is true")
    assert view.entities.summary('Openstack Hardware').get_text_of('Introspected') == 'true'


@pytest.mark.regression
def test_provide_host(host, provider, has_mistral_service):
    """Provide host
    Metadata:
        test_flag: openstack_scale

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    host.provide_node()
    wait_for(lambda: provider.mgmt.iapi.node.get(host.name).provision_state == 'available', delay=5,
             timeout=300)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    view = navigate_to(host, 'Details')
    prov_state = view.entities.summary('Openstack Hardware').get_text_of('Provisioning State')
    assert prov_state == 'available'


@pytest.mark.regression
def test_scale_provider_out(host, provider, has_mistral_service):
    """Scale out Infra provider
    Metadata:
        test_flag: openstack_scale

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    # Host has to be given a profile role before the scale out
    params = [{'path': '/properties/capabilities', 'value': 'profile:compute,boot_option:local',
               'op': 'replace'}]
    provider.mgmt.iapi.node.update(host.name, params)
    provider.scale_out(1)
    # This action takes usually a lot of time, so big delay and timeout are set
    wait_for(lambda: provider.mgmt.iapi.node.get(host.name).provision_state == 'active', delay=120,
             timeout=1800)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.name += ' (NovaCompute)'  # Host will change it's name after successful scale out
    host.browser.refresh()
    assert host.exists
    view = navigate_to(host, 'Details')
    prov_state = view.entities.summary('Openstack Hardware').get_text_of('Provisioning State')
    assert prov_state == 'active'
