import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.infrastructure import host as host_ui
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.update import update

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.smartstate,
    pytest.mark.meta(server_roles="+smartproxy +smartstate"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_VERSION),
    pytest.mark.usefixtures('setup_provider')
]

vddk_versions = [
    ('v6_0'),
    ('v6_5'),
    ('v6_7')
]


@pytest.fixture(scope="module")
def ssa_analysis_profile(appliance):
    collected_files = []
    for file in ["/etc/hosts", "/etc/passwd"]:
        collected_files.append({"Name": file, "Collect Contents?": True})

    analysis_profile_name = fauxfactory.gen_alphanumeric(18, start="ssa_analysis_")
    analysis_profile_collection = appliance.collections.analysis_profiles
    analysis_profile = analysis_profile_collection.create(
        name=analysis_profile_name,
        description=analysis_profile_name,
        profile_type=analysis_profile_collection.VM_TYPE,
        categories=["System"],
        files=collected_files)
    yield
    if analysis_profile.exists:
        analysis_profile.delete()


@pytest.fixture(params=vddk_versions, ids=([item for item in vddk_versions]), scope='function')
def configure_vddk(request, appliance, provider, vm):
    vddk_version = request.param
    vddk_url = conf.cfme_data.get("basic_info", {}).get("vddk_url", {}).get(vddk_version, None)
    if vddk_url is None:
        pytest.skip('Could not locate vddk url in cfme_data')
    else:
        appliance.install_vddk(vddk_url=vddk_url)
    view = navigate_to(vm, 'Details')
    host_name = view.entities.summary("Relationships").get_text_of("Host")
    host, = [host for host in provider.hosts.all() if host.name == host_name]
    host_data, = [data for data in provider.data['hosts'] if data['name'] == host.name]
    # TODO: Remove Host UI validation BZ:1718209
    # host.update_credentials_rest(credentials=host_data['credentials'])
    host_collection = appliance.collections.hosts
    host_obj = host_collection.instantiate(name=host.name, provider=provider)
    with update(host_obj, validate_credentials=True):
        host_obj.credentials = {'default': host_ui.Host.Credential.from_config(
                                host_data['credentials']['default'])}

    @request.addfinalizer
    def _finalize():
        appliance.uninstall_vddk()
        with update(host_obj):
            host_obj.credentials = {'default': host_ui.Host.Credential(
                principal="", secret="", verify_secret="")}


@pytest.fixture(scope="function")
def vm(request, provider, small_template, ssa_analysis_profile):
    """ Fixture to provision instance on the provider """
    vm_name = random_vm_name("ssa", max_length=16)
    vm_obj = provider.appliance.collections.infra_vms.instantiate(vm_name,
                                                                  provider,
                                                                  small_template.name)
    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm_obj.mgmt.ensure_state(VmState.RUNNING)

    @request.addfinalizer
    def _finalize():
        try:
            vm_obj.cleanup_on_provider()
            provider.refresh_provider_relationships()
        except Exception as e:
            logger.exception(e)

    return vm_obj


@pytest.mark.long_running
def test_ssa_vddk(vm, configure_vddk):
    """Check if different version of vddk works with provider


    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
    """
    vm.smartstate_scan(wait_for_task_result=True)
    view = navigate_to(vm, 'Details')
    c_users = view.entities.summary('Security').get_text_of('Users')
    c_groups = view.entities.summary('Security').get_text_of('Groups')
    assert any([c_users != 0, c_groups != 0])
