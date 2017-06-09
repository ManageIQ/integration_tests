# -*- coding: utf-8 -*-
""" Tests used to check whether assigned actions really do what they're supposed to do. Events are
note supported by ec2, gc and scvmm providers. Tests are uncollected for these
providers. When the support will be implemented these tests can enabled for them.

Required YAML keys:
    * Provider must have section provisioning/template (otherwise test will be skipped)
    * RHEV-M provider must have provisioning/vlan specified, otherwise the test fails on provis.
    * There should be a 'datastores_not_for_provision' in the root, being a list of datastores that
        should not be used for tagging for provisioning. If not present,
        nothing terrible happens, but provisioning can be then assigned to a datastore that does not
        work (iso datastore or whatever), therefore failing the provision.
"""
import fauxfactory
import pytest
from functools import partial

from cfme.common.provider import cleanup_vm
from cfme.common.vm import VM
from cfme.control.explorer import actions, policies, policy_profiles
from cfme.services import requests
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme import test_requirements
from utils import testgen
from utils.blockers import BZ
from utils.generators import random_vm_name
from utils.log import logger
from utils.hosts import setup_host_creds
from utils.virtual_machines import deploy_template
from utils.wait import wait_for, TimedOutError
from utils.pretty import Pretty
from . import vddk_url_map, do_scan, wait_for_ssa_enabled


pytest_generate_tests = testgen.generate(gen_func=testgen.all_providers, scope="module")

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(blockers=[
        BZ(
            1149128,
            unblock=lambda provider: not provider.one_of(SCVMMProvider))
    ]),
    pytest.mark.meta(server_roles="+automate +smartproxy +smartstate"),
    pytest.mark.tier(2),
    test_requirements.control
]


class VMWrapper(Pretty):
    """This class binds a provider_mgmt object with VM name. Useful for on/off operation"""
    __slots__ = ("_prov", "_vm", "api", "crud")
    pretty_attrs = ['_vm', '_prov']

    def __init__(self, provider, vm_name, api):
        self._prov = provider
        self._vm = vm_name
        self.api = api
        self.crud = VM.factory(vm_name, self._prov)

    @property
    def name(self):
        return self._vm

    @property
    def provider(self):
        return self._prov.mgmt

    def __getattr__(self, key):
        """Creates partial functions proxying to mgmt_system.<function_name>(vm_name)"""
        func = getattr(self._prov.mgmt, key)
        return partial(func, self._vm)


def get_vm_object(appliance, vm_name):
    """Looks up the CFME database for the VM.

    Args:
        vm_name: VM name

    Returns:
        If found, returns a REST object
        If not, `None`
    """
    try:
        return appliance.rest_api.collections.vms.find_by(name=vm_name)[0]
    except IndexError:
        return None


@pytest.fixture(scope="module")
def vm_name(provider):
    return random_vm_name("action", max_length=16)


@pytest.yield_fixture(scope="function")
def configure_fleecing(request, appliance, provider, vm):
    setup_host_creds(provider.key, vm.api.host.name)
    appliance.install_vddk(reboot=True, vddk_url=vddk_url_map[str(provider.version)])
    appliance.browser.quit_browser()
    yield
    appliance.uninstall_vddk()
    setup_host_creds(provider.key, vm.api.host.name, remove_creds=True)


def _get_vm(request, appliance, provider, template_name, vm_name):
    if provider.one_of(RHEVMProvider):
        kwargs = {"cluster": provider.data["default_cluster"]}
    elif provider.one_of(OpenStackProvider):
        kwargs = {}
        if 'small_template' in provider.data:
            kwargs = {"flavour_name": provider.data.get('small_template')}
    elif provider.one_of(SCVMMProvider):
        kwargs = {
            "host_group": provider.data.get("provisioning", {}).get("host_group", "All Hosts")}
    else:
        kwargs = {}

    try:
        deploy_template(
            provider.key,
            vm_name,
            template_name=template_name,
            allow_skip="default",
            power_on=True,
            **kwargs
        )
    except TimedOutError as e:
        logger.exception(e)
        try:
            provider.mgmt.delete_vm(vm_name)
        except TimedOutError:
            logger.warning("Could not delete VM %s!", vm_name)
        finally:
            # If this happened, we should skip all tests from this provider in this module
            pytest.skip("{} is quite likely overloaded! Check its status!\n{}: {}".format(
                provider.key, type(e).__name__, str(e)))

    @request.addfinalizer
    def _finalize():
        """if getting REST object failed, we would not get the VM deleted! So explicit teardown."""
        logger.info("Shutting down VM with name %s", vm_name)
        if (provider.one_of(InfraProvider, OpenStackProvider, AzureProvider) and
                provider.mgmt.is_vm_suspended(vm_name)):
            logger.info("Powering up VM %s to shut it down correctly.", vm_name)
            provider.mgmt.start_vm(vm_name)
        if provider.mgmt.is_vm_running(vm_name):
            logger.info("Powering off VM %s", vm_name)
            provider.mgmt.stop_vm(vm_name)
        if provider.mgmt.does_vm_exist(vm_name):
            logger.info("Deleting VM %s in %s", vm_name, provider.mgmt.__class__.__name__)
            provider.mgmt.delete_vm(vm_name)

    # Make it appear in the provider
    provider.refresh_provider_relationships()

    # Get the REST API object
    api = wait_for(
        lambda: get_vm_object(appliance, vm_name),
        message="VM object {} appears in CFME".format(vm_name),
        fail_condition=None,
        num_sec=600,
        delay=15,
    )[0]

    return VMWrapper(provider, vm_name, api)


@pytest.fixture(scope="function")
def vm(request, appliance, has_no_providers, provider, setup_provider, small_template, vm_name):
    return _get_vm(request, appliance, provider, small_template, vm_name)


@pytest.fixture(scope="function")
def vm_big(request, appliance, has_no_providers, provider, setup_provider, big_template, vm_name):
    return _get_vm(request, appliance, provider, big_template, vm_name)


@pytest.fixture(scope="module")
def name_suffix():
    return fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def policy_name(name_suffix):
    return "action_testing: policy {}".format(name_suffix)


@pytest.fixture(scope="module")
def policy_profile_name(name_suffix):
    return "action_testing: policy profile {}".format(name_suffix)


@pytest.fixture(scope="function")
def vm_on(vm):
    """ Ensures that the VM is on when the control goes to the test."""
    vm.wait_vm_steady()
    if not vm.is_vm_running():
        vm.start_vm()
        vm.wait_vm_running()
    # Make sure the state is consistent
    vm.crud.refresh_relationships(from_details=True)
    vm.crud.wait_for_vm_state_change(desired_state=vm.crud.STATE_ON, from_details=True)
    return vm


@pytest.fixture(scope="function")
def vm_off(provider, vm):
    """ Ensures that the VM is off when the control goes to the test."""
    vm.wait_vm_steady()
    if provider.one_of(InfraProvider, AzureProvider, OpenStackProvider) and vm.is_vm_suspended():
        vm.start_vm()
        vm.wait_vm_running()
    if not vm.is_vm_stopped():
        vm.stop_vm()
        vm.wait_vm_stopped()
    # Make sure the state is consistent
    vm.crud.refresh_relationships(from_details=True)
    vm.crud.wait_for_vm_state_change(desired_state=vm.crud.STATE_OFF, from_details=True)
    return vm


@pytest.yield_fixture(scope="module")
def policy_for_testing(vm_name, policy_name, policy_profile_name, provider):
    """Takes care of setting the appliance up for testing."""
    policy = policies.VMControlPolicy(
        policy_name,
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name)
    )
    policy.create()
    policy_profile = policy_profiles.PolicyProfile(policy_profile_name, policies=[policy])
    policy_profile.create()
    yield policy
    policy_profile.delete()
    policy.delete()


@pytest.yield_fixture(scope="function")
def assign_policy_for_testing(policy_for_testing, provider, policy_profile_name):
    provider.assign_policy_profiles(policy_profile_name)
    yield policy_for_testing
    provider.unassign_policy_profiles(policy_profile_name)


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_start_virtual_machine_after_stopping(request, vm, vm_on, assign_policy_for_testing):
    """ This test tests action 'Start Virtual Machine'

    This test sets the policy that it turns on the VM when it is turned off
    (https://www.youtube.com/watch?v=UOn4gxj2Dso), then turns the VM off and waits for it coming
    back alive.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power Off", ["Start Virtual Machine"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Stop the VM
    vm.stop_vm()
    # Wait for VM powered on by CFME
    try:
        wait_for(vm.is_vm_running, num_sec=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power on the VM {}".format(vm.name))


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_stop_virtual_machine_after_starting(request, vm, vm_off, assign_policy_for_testing):
    """ This test tests action 'Stop Virtual Machine'

    This test sets the policy that it turns off the VM when it is turned on
    (https://www.youtube.com/watch?v=UOn4gxj2Dso), then turns the VM on and waits for it coming
    back off.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On", ["Stop Virtual Machine"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Start the VM
    vm.start_vm()
    # Wait for VM powered off by CFME
    try:
        wait_for(vm.is_vm_stopped, num_sec=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power off the VM {}".format(vm.name))


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_suspend_virtual_machine_after_starting(request, vm, vm_off,
        assign_policy_for_testing):
    """ This test tests action 'Suspend Virtual Machine'

    This test sets the policy that it suspends the VM when it's turned on. Then it powers on the vm,
    waits for it becoming alive and then it waits for the VM being suspended.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On", ["Suspend Virtual Machine"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Start the VM
    vm.start_vm()
    # Wait for VM be suspended by CFME
    try:
        wait_for(vm.is_vm_suspended, num_sec=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not suspend the VM {}".format(vm.name))


@pytest.mark.meta(blockers=[1142875])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_prevent_event(request, vm, vm_off, assign_policy_for_testing):
    """ This test tests action 'Prevent current event from proceeding'

    This test sets the policy that it prevents powering the VM up. Then the vm is powered up
    and then it waits that VM does not come alive.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On Request",
                                                      ["Prevent current event from proceeding"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Request VM's start (through UI)
    vm.crud.power_control_from_cfme(vm.crud.POWER_ON, cancel=False)
    try:
        wait_for(vm.is_vm_running, num_sec=600, delay=5)
    except TimedOutError:
        pass  # VM did not start, so that's what we want
    else:
        pytest.fail("CFME did not prevent starting of the VM {}".format(vm.name))


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_power_on_logged(request, vm, vm_off, appliance, assign_policy_for_testing):
    """ This test tests action 'Generate log message'.

    This test sets the policy that it logs powering on of the VM. Then it powers up the vm and
    checks whether logs contain message about that.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On", ["Generate log message"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Start the VM
    vm.start_vm()
    policy_desc = assign_policy_for_testing.description

    # Search the logs
    def search_logs():
        rc, stdout = appliance.ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/policy.log | grep '{}'".format(policy_desc))
        if rc != 0:  # Nothing found, so shortcut
            return False
        for line in stdout.strip().split("\n"):
            if "Policy success" not in line:
                continue
            match_string = "policy: [{}], event: [VM Power On], entity name: [{}]".format(
                assign_policy_for_testing.description, vm.name)
            if match_string in line:
                logger.info("Found corresponding log message: %s", line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=180, message="log search")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_power_on_audit(request, vm, vm_off, appliance, assign_policy_for_testing):
    """ This test tests action 'Generate Audit Event'.

    This test sets the policy that it logs powering on of the VM. Then it powers up the vm and
    checks whether audit logs contain message about that.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On", ["Generate Audit Event"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Start the VM
    vm.start_vm()
    policy_desc = assign_policy_for_testing.description

    # Search the logs
    def search_logs():
        rc, stdout = appliance.ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/audit.log | grep '{}'".format(policy_desc)
        )
        if rc != 0:  # Nothing found, so shortcut
            return False
        for line in stdout.strip().split("\n"):
            if "Policy success" not in line or "MiqAction.action_audit" not in line:
                continue
            match_string = "policy: [{}], event: [VM Power On]".format(policy_desc)
            if match_string in line:
                logger.info("Found corresponding log message: %s", line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=180, message="log search")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_action_create_snapshot_and_delete_last(request, vm, vm_on, assign_policy_for_testing):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete Most Recent Snapshot'.

    This test sets the policy that it makes snapshot of VM after it's powered off and when it is
    powered back on, it deletes the last snapshot.

    Metadata:
        test_flag: actions, provision
    """
    if not hasattr(vm.crud, "total_snapshots"):
        pytest.skip("This provider does not support snapshots yet!")
    # Set up the policy and prepare finalizer
    snapshot_name = fauxfactory.gen_alphanumeric()
    snapshot_create_action = actions.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])
    assign_policy_for_testing.assign_actions_to_event("VM Power On",
                                                      ["Delete Most Recent Snapshot"])

    @request.addfinalizer
    def finalize():
        assign_policy_for_testing.assign_events()
        snapshot_create_action.delete()

    snapshots_before = vm.crud.total_snapshots
    # Power off to invoke snapshot creation
    vm.stop_vm()
    wait_for(lambda: vm.crud.total_snapshots > snapshots_before, num_sec=800,
             message="wait for snapshot appear", delay=5)
    assert vm.crud.current_snapshot_description == "Created by EVM Policy Action"
    assert vm.crud.current_snapshot_name == snapshot_name
    # Snapshot created and validated, so let's delete it
    snapshots_before = vm.crud.total_snapshots
    # Power on to invoke last snapshot deletion
    vm.start_vm()
    wait_for(lambda: vm.crud.total_snapshots < snapshots_before, num_sec=800,
             message="wait for snapshot deleted", delay=5)


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_action_create_snapshots_and_delete_them(request, vm, vm_on, assign_policy_for_testing):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete all Snapshots'.

    This test sets the policy that it makes snapshot of VM after it's powered off and then it cycles
    several time that it generates a couple of snapshots. Then the 'Delete all Snapshots' is
    assigned to power on event, VM is powered on and it waits for all snapshots to disappear.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    snapshot_name = fauxfactory.gen_alphanumeric()
    snapshot_create_action = actions.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])

    @request.addfinalizer
    def finalize():
        assign_policy_for_testing.assign_events()
        snapshot_create_action.delete()

    def create_one_snapshot(n):
        """
        Args:
            n: Sequential number of snapshot for logging.
        """
        # Power off to invoke snapshot creation
        snapshots_before = vm.crud.total_snapshots
        vm.stop_vm()
        wait_for(lambda: vm.crud.total_snapshots > snapshots_before, num_sec=800,
                 message="wait for snapshot %d to appear" % (n + 1), delay=5)
        current_snapshot = vm.crud.current_snapshot_name
        logger.debug('Current Snapshot Name: {}'.format(current_snapshot))
        assert current_snapshot == snapshot_name
        vm.start_vm()

    for i in range(4):
        create_one_snapshot(i)
    assign_policy_for_testing.assign_events()
    vm.stop_vm()
    assign_policy_for_testing.assign_actions_to_event("VM Power On", ["Delete all Snapshots"])
    # Power on to invoke all snapshots deletion
    vm.start_vm()
    wait_for(lambda: vm.crud.total_snapshots == 0, num_sec=800,
             message="wait for snapshots to be deleted", delay=5)


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_action_initiate_smartstate_analysis(request, configure_fleecing, vm, vm_off,
        assign_policy_for_testing):
    """ This test tests actions 'Initiate SmartState Analysis for VM'.

    This test sets the policy that it analyses VM after it's powered on. Then it checks whether
    that really happened.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On",
                                                      ["Initiate SmartState Analysis for VM"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Start the VM
    vm.crud.power_control_from_cfme(option=vm.crud.POWER_ON, cancel=False, from_details=True)
    vm.crud.load_details()
    wait_for_ssa_enabled()
    try:
        do_scan(vm.crud)
    except TimedOutError:
        pytest.fail("CFME did not finish analysing the VM {}".format(vm.name))


# TODO: Rework to use REST
# def test_action_raise_automation_event(
#         request, assign_policy_for_testing, vm, vm_on, ssh_client, vm_crud_refresh):
#     """ This test tests actions 'Raise Automation Event'.

#     This test sets the policy that it raises an automation event VM after it's powered on.
#     Then it checks logs whether that really happened.

#     Metadata:
#         test_flag: actions, provision
#     """
#     # Set up the policy and prepare finalizer
#     assign_policy_for_testing.assign_actions_to_event("VM Power Off", ["Raise Automation Event"])
#     request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
#     # Start the VM
#     vm.stop_vm()
#     vm_crud_refresh()

#     # Search the logs
#     def search_logs():
#         rc, stdout = ssh_client.run_command(
#             "cat /var/www/miq/vmdb/log/automation.log | grep 'MiqAeEvent.build_evm_event' |"
#             " grep 'event=<\"vm_poweroff\">' | grep 'id: {}'".format(vm.api.object.id)
#             # not guid, but the ID
#         )
#         if rc != 0:  # Nothing found, so shortcut
#             return False
#         found = [event for event in stdout.strip().split("\n") if len(event) > 0]
#         if not found:
#             return False
#         else:
#             logger.info("Found event: `%s`", event[-1].strip())
#             return True
#     wait_for(search_logs, num_sec=180, message="log search")


# Purely custom actions
@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_tag(request, vm, vm_off, assign_policy_for_testing):
    """ Tests action tag

    Metadata:
        test_flag: actions, provision
    """
    if any(tag.category.display_name == "Service Level" and tag.display_name == "Gold"
           for tag in vm.crud.get_tags()):
        vm.crud.remove_tag(("Service Level", "Gold"))

    tag_assign_action = actions.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Service Level", "Gold")}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power On", [tag_assign_action])

    @request.addfinalizer
    def finalize():
        assign_policy_for_testing.assign_events()
        tag_assign_action.delete()

    vm.start_vm()
    try:
        wait_for(
            lambda: any(tag.category.display_name == "Service Level" and tag.display_name == "Gold"
                        for tag in vm.crud.get_tags()),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not assigned!")


@pytest.mark.meta(blockers=[1205496])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider, RHEVMProvider,
    OpenStackProvider, AzureProvider))
def test_action_untag(request, vm, vm_off, assign_policy_for_testing):
    """ Tests action untag

    Metadata:
        test_flag: actions, provision
    """
    if not any(tag.category.display_name == "Service Level" and tag.display_name == "Gold"
           for tag in vm.crud.get_tags()):
        vm.crud.add_tag(("Service Level", "Gold"), single_value=True)

    @request.addfinalizer
    def _remove_tag():
        if any(tag.category.display_name == "Service Level" and tag.display_name == "Gold"
               for tag in vm.crud.get_tags()):
            vm.crud.remove_tag(("Service Level", "Gold"))

    tag_unassign_action = actions.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Remove Tags",
        action_values={"remove_tag": ["Service Level"]}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power On", [tag_unassign_action])

    @request.addfinalizer
    def finalize():
        assign_policy_for_testing.assign_events()
        tag_unassign_action.delete()

    vm.start_vm()
    try:

        wait_for(
            lambda: not any(tag.category.display_name == "Service Level" and
                            tag.display_name == "Gold" for tag in vm.crud.get_tags()),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not unassigned!")


@pytest.mark.meta(blockers=[1381255])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_action_cancel_clone(request, provider, vm_big, assign_policy_for_testing):
    """This test checks if 'Cancel vCenter task' action works.
    For this test we need big template otherwise CFME won't have enough time
    to cancel the task https://bugzilla.redhat.com/show_bug.cgi?id=1383372#c9
    """
    assign_policy_for_testing.assign_events("VM Clone Start")
    assign_policy_for_testing.assign_actions_to_event(
        "VM Clone Start", ["Cancel vCenter Task"])
    clone_vm_name = "{}-clone".format(vm_big.name)
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    request.addfinalizer(lambda: cleanup_vm(clone_vm_name, provider))
    vm_big.crud.clone_vm(fauxfactory.gen_email(), "first", "last", clone_vm_name, "VMware")
    cells = {"Description": clone_vm_name}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=4000, delay=20)
    assert row.status.text == "Error"
