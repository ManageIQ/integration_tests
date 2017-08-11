import pytest


from cfme.exceptions import HostNotFound
from cfme.infrastructure.host import get_all_hosts, Host
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import flash
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.wait import RefreshTimer, wait_for


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.fixture(scope='module')
def host(provider):
    """Find a host for test scenario"""
    view = navigate_to(Host, 'All')
    hosts = view.entities.get_all()
    # Find a compute host with no instances on it
    for h in hosts:
        if 'Compute' in h.name and h.quad_entity(h.name).no_vm == 0:
            return Host(h.name, provider=provider)
    raise HostNotFound('There is no proper host for tests')


def test_scale_provider_down(provider, host):
    """Scale down Openstack Infrastructure provider
    Metadata:
        test_flag: openstack_scale"""
    host.toggle_maintenance_mode()
    flash.assert_success()
    host_uuid = host.name.split()[0]  # cut off deployment role part from host's name
    wait_for(lambda: provider.mgmt.iapi.node.get(host_uuid).maintenance, timeout=600, delay=5)
    wait_for(provider.is_refreshed, [RefreshTimer(400)], timeout=600)
    assert host.get_detail('Properties', 'Maintenance Mode') == 'Enabled'
    provider.scale_down(host_uuid)
    flash.assert_success()
    provider.mgmt.iapi.node.wait_for_provision_state(host_uuid, 'available', timeout=1200)
    wait_for(provider.is_refreshed, [RefreshTimer(400)], timeout=600)  # Refresh again
    host.name = host_uuid  # host's name is changed after scale down
    assert host.get_detail('Openstack Hardware', 'Provisioning State') == 'available'


@pytest.mark.requires_test('test_scale_provider_down')
def test_delete_host(host, provider):
    """Remove host from appliance and Ironic service"""
    def is_host_disappeared():
        return host.name not in [h.uuid for h in provider.mgmt.iapi.node.list()]

    host.delete(cancel=False)
    wait_for(is_host_disappeared, timeout=300, delay=5)
    wait_for(provider.is_refreshed, [RefreshTimer(400)], timeout=600)
    assert host.name not in get_all_hosts()


@pytest.mark.requires_test('test_delete_host')
def test_register_host(provider, host):
    """Register new host by uploading instackenv.json file"""
    hosts_before = [h.uuid for h in provider.mgmt.iapi.node.list()]
    provider.register(provider.get_yaml_data()['instackenv_file_path'])
    flash.assert_success()
    # Wait for a new host to appear
    wait_for(lambda: len(provider.mgmt.iapi.node.list()) == len(hosts_before) + 1, timeout=300,
             delay=5)
    hosts_after = [h.uuid for h in provider.mgmt.iapi.node.list()]
    # Look for a UUID of newly created host
    for h in hosts_after:
        if h not in hosts_before:
            host.name = h
    wait_for(provider.is_refreshed, [RefreshTimer(400)], timeout=600)
    assert host.exists()


@pytest.mark.requires_test('test_register_host')
def test_introspect_host(host, provider):
    """Introspect host"""
    host.run_introspection()
    wait_for(lambda: provider.mgmt.iapi.node.get(host.name).inspection_finished_at, delay=15,
             timeout=600)
    wait_for(provider.is_refreshed, [RefreshTimer(400)], timeout=600)
    assert host.get_detail('Openstack Hardware', 'Introspected') == 'true'


@pytest.mark.requires_test('test_register_host')
def test_provide_host(host, provider):
    """Provide host"""
    host.provide_node()
    provider.mgmt.iapi.node.wait_for_provision_state(host.name, 'available', timeout=300)
    wait_for(provider.is_refreshed, [RefreshTimer(400)], timeout=600)
    assert host.get_detail('Openstack Hardware', 'Provisioning State') == 'available'


@pytest.mark.requires_test('test_provide_host')
def test_scale_provider_out(host, provider):
    """Scale out Infra provider"""
    # Host has to be given a profile role before the scale out
    params = [{'path': '/properties/capabilities', 'value': 'profile:compute,boot_option:local',
               'op': 'replace'}]
    provider.mgmt.iapi.node.update(host.name, params)
    provider.scale_out(1)
    flash.assert_success()
    # This action takes usually a lot of time, so big delay and timeout are set
    wait_for(lambda: provider.mgmt.iapi.node.get(host.name).provision_state == 'active', delay=120,
             timeout=1200)
    wait_for(provider.is_refreshed, [RefreshTimer(400)], timeout=600)
    host.name += ' (NovaCompute)'  # Host will change it's name after successful scale out
    assert host.exists()
    assert host.get_detail('Openstack Hardware', 'Provisioning State') == 'active'
