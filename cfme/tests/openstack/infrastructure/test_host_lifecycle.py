import pytest


from cfme.configure.tasks import is_host_analysis_finished
from cfme.exceptions import HostNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.host import get_all_hosts, Host, wait_for_host_delete
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import InfoBlock, Quadicon, toolbar, flash
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
    """Scale down Openstack Infrastructure provider"""
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
def test_delete_host(host):
    """Remove host from appliance and Ironic service"""
    host.delete(cancel=False)
    wait_for_host_delete(host)
    assert host.name not in get_all_hosts()


# @pytest.mark.requires_test('test_delete_host')
# def test_register_host(provider):
#     """Register new host by uploading instackenv.json file"""
#     provider.register(provider.get_yaml_data()['instackenv_file_path'])
#     flash.assert_success()
#     wait_for(lambda: provider.mgmt.iapi.node.)