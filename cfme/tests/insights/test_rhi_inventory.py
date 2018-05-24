# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.configure.configuration.analysis_profile import AnalysisProfile
from cfme.configure.configuration.region_settings import RedHatUpdates
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils import conf, ssh
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.hosts import setup_host_creds
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, wait_for_decorator


pytestmark = [
    test_requirements.insights,
    pytest.mark.meta(server_roles="+smartproxy +smartstate"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_VERSION, required_fields=[
        ['vm_analysis_new', 'provisioning', 'vlan'],
        ['vm_analysis_new', 'provisioning', 'host'],
        ['vm_analysis_new', 'provisioning', 'datastore']]),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture
def register_appliance(request, appliance, reg_method='rhsm'):
    red_hat_updates = RedHatUpdates(service='rhsm', url='subscription.rhn.redhat.com',
                                    username=conf.credentials[reg_method]['username'],
                                    password=conf.credentials[reg_method]['password'])

    if not red_hat_updates.is_registered:
        red_hat_updates.update_registration()

        red_hat_updates.register_appliances()
        wait_for(
            func=red_hat_updates.is_registering,
            func_args=[appliance.server.name],
            delay=10,
            num_sec=300,
            fail_func=red_hat_updates.refresh
        )

        wait_for(
            func=red_hat_updates.is_registered,
            func_args=[appliance.server.name],
            delay=20,
            num_sec=500,
            fail_func=red_hat_updates.refresh
        )
    request.addfinalizer(appliance.unregister)


@pytest.fixture(scope="module")
def ssa_analysis_profile():
    collected_files = []
    for file in ["/etc/hosts", "/etc/passwd", "/etc/redhat-access-insights/machine-id"]:
        collected_files.append({"Name": file, "Collect Contents?": True})

    analysis_profile_name = 'default'
    analysis_profile = AnalysisProfile(
        name=analysis_profile_name,
        description=analysis_profile_name,
        profile_type=AnalysisProfile.VM_TYPE,
        categories=["System"],
        files=collected_files
    )
    analysis_profile.create()
    yield analysis_profile
    analysis_profile.delete()


@pytest.fixture
def vm(request, provider, ssa_analysis_profile, register_appliance):
    """ Fixture to provision instance on the provider """
    # TODO use fauxfactory instead of random_vms
    vm_name = 'test-rhi-{}'.format(fauxfactory.gen_alphanumeric())
    vm_data = provider.data.vm_analysis_new
    provisioning_data = vm_data.provisioning
    vm_obj = VM.factory(vm_name, provider, template_name=vm_data['vms']['rhel74']['image'])
    vm_obj.create_on_provider(find_in_cfme=True, **provisioning_data)
    logger.info("VM %s provisioned, waiting for IP address to be assigned", vm_name)

    @wait_for_decorator(timeout="22m", delay=5)
    def get_ip_address():
        if provider.mgmt.is_vm_stopped(vm_name):
            provider.mgmt.start_vm(vm_name)
        ip = provider.mgmt.current_ip_address(vm_name)
        logger.info("Fetched IP for %s: %s", vm_name, ip)
        return ip is not None

    connect_ip = provider.mgmt.get_ip_address(vm_name)
    assert connect_ip is not None
    if connect_ip:
        ssh_client = ssh.SSHClient(
            hostname=connect_ip,
            username=credentials[provisioning_data.credentials]['username'],
            password=credentials[provisioning_data.credentials]['password'],
            port=22)
        # TODO: Add another tag in cfme_yaml file to distinguish RHI VM
        username = conf.credentials['rhsm']['username']
        password = conf.credentials['rhsm']['password']
        ssh_client.run_command('subscription-manager register --username {} --password {}'.format(
            username, password))
        ssh_client.run_command('subscription-manager attach --auto')
        ssh_client.run_command('yum install redhat-access-insights -y')
        ssh_client.run_command('redhat-access-insights --register')

    @request.addfinalizer
    def _finalize():
        try:
            vm_obj.cleanup_on_provider()
            provider.refresh_provider_relationships()
        except Exception as e:
            logger.exception(e)

    return vm_obj


@pytest.fixture
def configure_provider(request, appliance, vm, provider):
    view = navigate_to(vm, 'Details')
    host = view.entities.summary("Relationships").get_text_of("Host")
    setup_host_creds(provider, host)
    appliance.install_vddk()
    yield vm

    @request.addfinalizer
    def _finalize():
        appliance.uninstall_vddk()
        setup_host_creds(provider, host, remove_creds=True)


@pytest.mark.long_running
@pytest.mark.tier(1)
def test_rhi_inventory(appliance, provider, setup_provider, configure_provider, vm):

    vm.smartstate_scan(wait_for_task_result=True)
    # Check that all data has been fetched
    view = navigate_to(vm, 'Details')
    current = view.entities.summary('Configuration').get_text_of('Files')
    assert current != '0', "No files were scanned"

    collection = appliance.collections.rh_insights
    view = navigate_to(collection, 'Inventory')
    system_count = view.systems.read()
    count = int(system_count.split()[0])
    assert count != 0, "No Systems were registered for Insights"
