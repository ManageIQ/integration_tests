import pytest

from cfme.exceptions import HostNotFound
from cfme.infrastructure.openstack_node import OpenstackNode
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.fixture(scope='module')
def host(provider):
    """Find a host for test scenario"""
    view = navigate_to(OpenstackNode, 'All')
    hosts = view.entities.get_all()
    # Find a compute host with no instances on it
    for h in hosts:
        if 'Compute' in h.name and h.data['no_vm'] == 0:
            return OpenstackNode(h.name, provider=provider)
    raise HostNotFound('There is no proper host for tests')


@pytest.fixture(scope='module')
def has_mistral_service(provider):
    """Skip test if there is no Mistral service on OSPd provider"""
    services = provider.mgmt.kapi.services.list()
    if 'mistral' not in [s.name for s in services]:
        pytest.skip('Skipping because no Mistral service found on OSPD deployment')


def test_scale_provider_down(provider, host, has_mistral_service):
    """Scale down Openstack Infrastructure provider
    Metadata:
        test_flag: openstack_scale"""
    host.toggle_maintenance_mode()
    host_uuid = host.name.split()[0]  # cut off deployment role part from host's name
    wait_for(lambda: provider.mgmt.iapi.node.get(host_uuid).maintenance, timeout=600, delay=5)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    assert host.get_detail('Properties', 'Maintenance Mode') == 'Enabled'
    provider.scale_down()
    wait_for(lambda: provider.mgmt.iapi.node.get(host_uuid).provision_state == 'available', delay=5,
             timeout=1200)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.name = host_uuid  # host's name is changed after scale down
    host.browser.refresh()
    assert host.get_detail('Openstack Hardware', 'Provisioning State') == 'available'


def test_delete_host(appliance, host, provider, has_mistral_service):
    """Remove host from appliance and Ironic service
    Metadata:
        test_flag: openstack_scale"""
    def is_host_disappeared():
        return host.name not in [h.uuid for h in provider.mgmt.iapi.node.list()]

    host.delete(cancel=False)
    wait_for(is_host_disappeared, timeout=300, delay=5)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    host_collection = appliance.collections.hosts
    assert host.name not in host_collection.all(provider)


def test_register_host(provider, host, has_mistral_service):
    """Register new host by uploading instackenv.json file
    Metadata:
        test_flag: openstack_scale"""
    hosts_before = [h.uuid for h in provider.mgmt.iapi.node.list()]
    provider.register(provider.get_yaml_data()['instackenv_file_path'])
    # Wait for a new host to appear
    wait_for(lambda: len(provider.mgmt.iapi.node.list()) == len(hosts_before) + 1, timeout=300,
             delay=5)
    hosts_after = [h.uuid for h in provider.mgmt.iapi.node.list()]
    # Look for a UUID of newly created host
    for h in hosts_after:
        if h not in hosts_before:
            host.name = h
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    assert host.exists


def test_introspect_host(host, provider, has_mistral_service):
    """Introspect host
    Metadata:
        test_flag: openstack_scale"""
    host.run_introspection()
    wait_for(lambda: provider.mgmt.iapi.node.get(host.name).inspection_finished_at, delay=15,
             timeout=600)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    assert host.get_detail('Openstack Hardware', 'Introspected') == 'true'


def test_provide_host(host, provider, has_mistral_service):
    """Provide host
    Metadata:
        test_flag: openstack_scale"""
    host.provide_node()
    wait_for(lambda: provider.mgmt.iapi.node.get(host.name).provision_state == 'available', delay=5,
             timeout=300)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    host.browser.refresh()
    assert host.get_detail('Openstack Hardware', 'Provisioning State') == 'available'


def test_scale_provider_out(host, provider, has_mistral_service):
    """Scale out Infra provider
    Metadata:
        test_flag: openstack_scale"""
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
    assert host.get_detail('Openstack Hardware', 'Provisioning State') == 'active'
