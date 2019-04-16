# -*- coding: utf-8 -*-
""" Tests used to check whether assigned actions really do what they're supposed to do. Events are
not supported by gc and scvmm providers. Tests are uncollected for these
providers. When the support will be implemented these tests can enabled for them.

Required YAML keys:
    * Provider must have section provisioning/template (otherwise test will be skipped)
    * RHEV-M provider must have provisioning/vlan specified, otherwise the test fails on provis.
    * There should be a 'datastores_not_for_provision' in the root, being a list of datastores that
        should not be used for tagging for provisioning. If not present,
        nothing terrible happens, but provisioning can be then assigned to a datastore that does not
        work (iso datastore or whatever), therefore failing the provision.
"""
from functools import partial

import fauxfactory
import pytest
from wrapanapi import VmState

from . import do_scan
from . import wait_for_ssa_enabled
from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.control.explorer import conditions
from cfme.control.explorer import policies
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import update
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles="+automate +smartproxy +smartstate"),
    pytest.mark.tier(2),
    test_requirements.control
]


class VMWrapper(Pretty):
    """This class binds a provider_mgmt object with VM name. Useful for on/off operation"""
    __slots__ = ("_prov", "_vm", "api")
    pretty_attrs = ['_vm', '_prov']

    def __init__(self, provider, vm_name, api):
        self._prov = provider
        self._vm = vm_name
        self.api = api

    @property
    def crud(self):
        """Instantiate BaseVM derived class for correct provider type"""
        collection = self._prov.appliance.provider_based_collection(self._prov)
        return collection.instantiate(self.name, self._prov)

    @property
    def mgmt(self):
        return self.crud.mgmt

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


def _get_vm(request, provider, template_name, vm_name):
    if provider.one_of(RHEVMProvider):
        kwargs = {"cluster": provider.data["default_cluster"]}
    elif provider.one_of(OpenStackProvider):
        kwargs = {}
        if 'small_template' in provider.data.templates:
            kwargs = {"flavor_name": provider.data.provisioning.get('instance_type')}
    elif provider.one_of(SCVMMProvider):
        kwargs = {
            "host_group": provider.data.get("provisioning", {}).get("host_group", "All Hosts")}
    else:
        kwargs = {}

    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(vm_name, provider, template_name)

    try:
        deploy_template(
            provider.key,
            vm_name,
            template_name=template_name,
            allow_skip="default",
            power_on=True,
            **kwargs
        )
    except TimedOutError:
        message = "{} failed provisioning, check its status!".format(provider.key)
        logger.exception(message)
        try:
            vm.cleanup_on_provider()
        except TimedOutError:
            logger.error("Could not delete VM %s!", vm_name)
        # If this happened, we should skip all tests from this provider in this module
        pytest.skip(message)

    request.addfinalizer(vm.cleanup_on_provider)

    # Make it appear in the provider
    provider.refresh_provider_relationships()

    # Get the REST API object
    api = wait_for(
        get_vm_object,
        func_args=[provider.appliance, vm_name],
        message="VM object {} appears in CFME".format(vm),
        fail_condition=None,
        num_sec=600,
        delay=15,
    )[0]

    return VMWrapper(provider, vm_name, api)


@pytest.fixture(scope="module")
def vm(request, provider, setup_provider_modscope, small_template_modscope, vm_name):
    return _get_vm(request, provider, small_template_modscope.name, vm_name)


@pytest.fixture(scope="module")
def vm_big(request, provider, setup_provider_modscope, big_template_modscope):
    return _get_vm(
        request,
        provider,
        big_template_modscope.name,
        random_vm_name("action", max_length=16)
    )


@pytest.fixture(scope="module")
def policy_name():
    return "action_testing: policy {}".format(fauxfactory.gen_alphanumeric())


@pytest.fixture(scope="module")
def policy_profile_name():
    return "action_testing: policy profile {}".format(fauxfactory.gen_alphanumeric())


@pytest.fixture(scope="module")
def compliance_condition(appliance):
    condition_collection = appliance.collections.conditions
    _compliance_condition = condition_collection.create(
        conditions.VMCondition,
        fauxfactory.gen_alpha(),
        expression="fill_tag(VM and Instance.My Company Tags : Service Level, Gold)"
    )
    yield _compliance_condition
    _compliance_condition.delete()


@pytest.fixture(scope="module")
def compliance_policy(vm_name, policy_name, appliance):
    compliance_policy = appliance.collections.policies.create(
        policies.VMCompliancePolicy,
        "complaince_{}".format(policy_name),
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name)
    )
    return compliance_policy


@pytest.fixture(scope="module")
def policy_for_testing(provider, vm_name, policy_name, policy_profile_name, compliance_policy,
        compliance_condition, appliance):
    control_policy = appliance.collections.policies.create(
        policies.VMControlPolicy,
        policy_name,
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name)
    )
    policy_profile_collection = appliance.collections.policy_profiles
    policy_profile = policy_profile_collection.create(
        policy_profile_name,
        policies=[control_policy, compliance_policy]
    )
    provider.assign_policy_profiles(policy_profile_name)
    yield control_policy
    provider.unassign_policy_profiles(policy_profile_name)
    policy_profile.delete()
    compliance_policy.delete()
    control_policy.delete()


@pytest.fixture(scope="module")
def host(provider, setup_provider_modscope):
    return provider.hosts.all()[0]


@pytest.fixture(scope="module")
def host_policy(appliance, host):
    control_policy = appliance.collections.policies.create(
        policies.HostControlPolicy,
        "action_testing: host policy {}".format(fauxfactory.gen_alphanumeric())
    )
    policy_profile_collection = appliance.collections.policy_profiles
    policy_profile = policy_profile_collection.create(
        "action_testing: host policy profile {}".format(fauxfactory.gen_alphanumeric()),
        policies=[control_policy]
    )
    host.assign_policy_profiles(policy_profile.description)
    yield control_policy
    host.unassign_policy_profiles(policy_profile.description)
    policy_profile.delete()
    control_policy.delete()


@pytest.fixture(scope="function")
def vm_on(vm):
    """ Ensures that the VM is on when the control goes to the test."""
    vm.mgmt.wait_for_steady_state()
    vm.mgmt.ensure_state(VmState.RUNNING)
    # Make sure the state is consistent
    vm.crud.refresh_relationships(from_details=True)
    vm.crud.wait_for_vm_state_change(desired_state=vm.crud.STATE_ON, from_details=True)
    return vm


@pytest.fixture(scope="function")
def vm_off(provider, vm):
    """ Ensures that the VM is off when the control goes to the test."""
    vm.mgmt.wait_for_steady_state()
    vm.mgmt.ensure_state(VmState.STOPPED)
    # Make sure the state is consistent
    vm.crud.refresh_relationships(from_details=True)
    vm.crud.wait_for_vm_state_change(desired_state=vm.crud.STATE_OFF, from_details=True)
    return vm


@pytest.mark.rhel_testing
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_start_virtual_machine_after_stopping(request, vm, vm_on, policy_for_testing):
    """ This test tests action 'Start Virtual Machine'

    This test sets the policy that it turns on the VM when it is turned off
    (https://www.youtube.com/watch?v=UOn4gxj2Dso), then turns the VM off and waits for it coming
    back alive.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power Off", ["Start Virtual Machine"])
    request.addfinalizer(policy_for_testing.assign_events)
    # Stop the VM
    vm.mgmt.stop()
    # Wait for VM powered on by CFME
    try:
        vm.mgmt.wait_for_state(VmState.RUNNING, timeout=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power on the VM {}".format(vm.name))


@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_stop_virtual_machine_after_starting(request, vm, vm_off, policy_for_testing):
    """ This test tests action 'Stop Virtual Machine'

    This test sets the policy that it turns off the VM when it is turned on
    (https://www.youtube.com/watch?v=UOn4gxj2Dso), then turns the VM on and waits for it coming
    back off.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Stop Virtual Machine"])
    request.addfinalizer(policy_for_testing.assign_events)
    # Start the VM
    vm.mgmt.start()
    # Wait for VM powered off by CFME
    try:
        vm.mgmt.wait_for_state(VmState.STOPPED, timeout=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power off the VM {}".format(vm.name))


@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_suspend_virtual_machine_after_starting(request, vm, vm_off, policy_for_testing):
    """ This test tests action 'Suspend Virtual Machine'

    This test sets the policy that it suspends the VM when it's turned on. Then it powers on the vm,
    waits for it becoming alive and then it waits for the VM being suspended.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Suspend Virtual Machine"])
    request.addfinalizer(policy_for_testing.assign_events)
    # Start the VM
    vm.mgmt.start()
    # Wait for VM be suspended by CFME
    try:
        vm.mgmt.wait_for_state(VmState.SUSPENDED, timeout=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not suspend the VM {}".format(vm.name))


@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_prevent_event(request, vm, vm_off, policy_for_testing):
    """ This test tests action 'Prevent current event from proceeding'

    This test sets the policy that it prevents powering the VM up. Then the vm is powered up
    and then it waits that VM does not come alive.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On Request",
        ["Prevent current event from proceeding"])
    request.addfinalizer(policy_for_testing.assign_events)
    # Request VM's start (through UI)
    vm.crud.power_control_from_cfme(option=vm.crud.POWER_ON, cancel=False)
    try:
        vm.mgmt.wait_for_state(VmState.RUNNING, timeout=600, delay=5)
    except TimedOutError:
        pass  # VM did not start, so that's what we want
    else:
        pytest.fail("CFME did not prevent starting of the VM {}".format(vm.name))


@pytest.mark.meta(blockers=[BZ(1439331)])
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_prevent_vm_retire(request, vm, vm_on, policy_for_testing):
    """This test sets the policy that prevents VM retiring.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    policy_for_testing.assign_actions_to_event("VM Retire Request",
        ["Prevent current event from proceeding"])
    request.addfinalizer(policy_for_testing.assign_events)
    vm.crud.retire()
    try:
        wait_for(lambda: vm.crud.is_retired, num_sec=600, delay=15,
                 message="Waiting for vm retiring")
    except TimedOutError:
        pass
    else:
        pytest.fail("CFME did not prevent retire of the VM {}".format(vm.name))


@pytest.mark.provider([VMwareProvider], scope="module")
def test_action_prevent_ssa(request, appliance, configure_fleecing, vm, vm_on, policy_for_testing):
    """Tests preventing Smart State Analysis.

    This test sets the policy that prevents VM analysis.
    https://bugzilla.redhat.com/show_bug.cgi?id=1433084

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control
    """
    policy_for_testing.assign_actions_to_event("VM Analysis Request",
        ["Prevent current event from proceeding"])
    request.addfinalizer(policy_for_testing.assign_events)
    wait_for_ssa_enabled(vm.crud)
    try:
        do_scan(vm.crud)
    except TimedOutError:
        result = appliance.ssh_client.run_command(
            "grep 'Prevent current event from proceeding.*VM Analysis Request.*{}'"
            " /var/www/miq/vmdb/log/policy.log".format(vm.name)
        )
        assert result.success, 'Action "Prevent current event from proceeding" hasn\'t been invoked'
    else:
        pytest.fail("CFME did not prevent analysing the VM {}".format(vm.name))


@pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module")
def test_action_prevent_host_ssa(request, appliance, host, host_policy):
    """Tests preventing Smart State Analysis on a host.

    This test sets the policy that prevents host analysis.
    https://bugzilla.redhat.com/show_bug.cgi?id=1437910

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control
    """
    host_policy.assign_actions_to_event("Host Analysis Request",
        ["Prevent current event from proceeding"])
    request.addfinalizer(host_policy.assign_events)
    view = navigate_to(host, "Details")

    def _scan():
        return view.entities.summary("Relationships").get_text_of("Drift History")

    original = _scan()
    view.toolbar.configuration.item_select("Perform SmartState Analysis", handle_alert=True)
    view.flash.assert_success_message('"{}": Analysis successfully initiated'.format(host.name))
    try:
        wait_for(
            lambda: _scan() != original,
            num_sec=60, delay=5, fail_func=view.browser.refresh,
            message="Check if Drift History field is changed")
    except TimedOutError:
        event_string = 'Prevent current event from proceeding'
        result = appliance.ssh_client.run_command(
            "grep '{}.*Host Analysis Request.*{}' /var/www/miq/vmdb/log/policy.log"
            .format(event_string, host.name)
        )
        assert result.success, 'Action "{}" has not been invoked'.format(event_string)
    else:
        pytest.fail("CFME did not prevent analysing the Host {}".format(host.name))


@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_power_on_logged(request, vm, vm_off, appliance, policy_for_testing):
    """ This test tests action 'Generate log message'.

    This test sets the policy that it logs powering on of the VM. Then it powers up the vm and
    checks whether logs contain message about that.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Generate log message"])
    request.addfinalizer(policy_for_testing.assign_events)
    # Start the VM
    vm.mgmt.start()
    policy_desc = policy_for_testing.description

    # Search the logs
    def search_logs():
        result = appliance.ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/policy.log | grep '{}'".format(policy_desc))
        if result.failed:  # Nothing found, so shortcut
            return False
        for line in result.output.strip().split("\n"):
            if "Policy success" not in line:
                continue
            match_string = "policy: [{}], event: [VM Power On], entity name: [{}]".format(
                policy_desc, vm.name)
            if match_string in line:
                logger.info("Found corresponding log message: %s", line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=180, message="log search")


@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_power_on_audit(request, vm, vm_off, appliance, policy_for_testing):
    """ This test tests action 'Generate Audit Event'.

    This test sets the policy that it logs powering on of the VM. Then it powers up the vm and
    checks whether audit logs contain message about that.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Generate Audit Event"])
    request.addfinalizer(policy_for_testing.assign_events)
    # Start the VM
    vm.mgmt.start()
    policy_desc = policy_for_testing.description

    # Search the logs
    def search_logs():
        result = appliance.ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/audit.log | grep '{}'".format(policy_desc)
        )
        if result.failed:  # Nothing found, so shortcut
            return False
        for line in result.output.strip().split("\n"):
            if "Policy success" not in line or "MiqAction.action_audit" not in line:
                continue
            match_string = "policy: [{}], event: [VM Power On]".format(policy_desc)
            if match_string in line:
                logger.info("Found corresponding log message: %s", line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=180, message="log search")


@pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module")
def test_action_create_snapshot_and_delete_last(
    appliance,
    request,
    vm,
    vm_on,
    policy_for_testing,
    provider
):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete Most Recent Snapshot'.

    This test sets the policy that it makes snapshot of VM after it's powered off and when it is
    powered back on, it deletes the last snapshot.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    snapshot_name = fauxfactory.gen_alphanumeric()
    snapshot_create_action = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])
    policy_for_testing.assign_actions_to_event("VM Power On", ["Delete Most Recent Snapshot"])

    @request.addfinalizer
    def finalize():
        policy_for_testing.assign_events()
        snapshot_create_action.delete()

    snapshots_before = vm.crud.total_snapshots
    # Power off to invoke snapshot creation
    vm.mgmt.stop()
    wait_for(lambda: vm.crud.total_snapshots > snapshots_before, num_sec=800,
             message="wait for snapshot appear", delay=5)
    assert vm.crud.current_snapshot_description == "Created by EVM Policy Action"
    assert vm.crud.current_snapshot_name == snapshot_name
    # Snapshot created and validated, so let's delete it
    snapshots_before = vm.crud.total_snapshots
    # Power on to invoke last snapshot deletion
    vm.mgmt.start()
    wait_for(lambda: vm.crud.total_snapshots < snapshots_before, num_sec=800,
             message="wait for snapshot deleted", delay=5)


@pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module")
def test_action_create_snapshots_and_delete_them(request, appliance, vm, vm_on,
        policy_for_testing, provider):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete all Snapshots'.

    This test sets the policy that it makes snapshot of VM after it's powered off and then it cycles
    several time that it generates a couple of snapshots. Then the 'Delete all Snapshots' is
    assigned to power on event, VM is powered on and it waits for all snapshots to disappear.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    snapshot_name = fauxfactory.gen_alphanumeric()
    snapshot_create_action = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])

    @request.addfinalizer
    def finalize():
        policy_for_testing.assign_events()
        snapshot_create_action.delete()

    def create_one_snapshot(n):
        """
        Args:
            n: Sequential number of snapshot for logging.
        """
        # Power off to invoke snapshot creation
        snapshots_before = vm.crud.total_snapshots
        vm.mgmt.stop()
        wait_for(lambda: vm.crud.total_snapshots > snapshots_before, num_sec=800,
                 message="wait for snapshot %d to appear" % (n + 1), delay=5)
        current_snapshot = vm.crud.current_snapshot_name
        logger.debug('Current Snapshot Name: {}'.format(current_snapshot))
        assert current_snapshot == snapshot_name
        vm.mgmt.start()

    for i in range(4):
        create_one_snapshot(i)
    policy_for_testing.assign_events()
    vm.mgmt.stop()
    policy_for_testing.assign_actions_to_event("VM Power On", ["Delete all Snapshots"])
    # Power on to invoke all snapshots deletion
    vm.mgmt.start()
    wait_for(lambda: vm.crud.total_snapshots == 0, num_sec=800,
             message="wait for snapshots to be deleted", delay=5)


@pytest.mark.provider([VMwareProvider], scope="module")
def test_action_initiate_smartstate_analysis(request, configure_fleecing, vm, vm_off,
        policy_for_testing):
    """ This test tests actions 'Initiate SmartState Analysis for VM'.

    This test sets the policy that it analyses VM after it's powered on. Then it checks whether
    that really happened.

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On",
        ["Initiate SmartState Analysis for VM"])
    request.addfinalizer(policy_for_testing.assign_events)
    # Start the VM
    vm.crud.power_control_from_cfme(option=vm.crud.POWER_ON, cancel=False, from_details=True)
    wait_for_ssa_enabled(vm.crud)
    try:
        do_scan(vm.crud)
    except TimedOutError:
        pytest.fail("CFME did not finish analysing the VM {}".format(vm.name))


# TODO: Rework to use REST
# def test_action_raise_automation_event(
#         request, policy_for_testing, vm, vm_on, ssh_client, vm_crud_refresh):
#     """ This test tests actions 'Raise Automation Event'.

#     This test sets the policy that it raises an automation event VM after it's powered on.
#     Then it checks logs whether that really happened.

#     Metadata:
#         test_flag: actions, provision
#     """
#     # Set up the policy and prepare finalizer
#     policy_for_testing.assign_actions_to_event("VM Power Off", ["Raise Automation Event"])
#     request.addfinalizer(lambda: policy_for_testing.assign_events())
#     # Start the VM
#     vm.mgmt.stop()
#     vm_crud_refresh()

#     # Search the logs
#     def search_logs():
#         result = ssh_client.run_command(
#             "cat /var/www/miq/vmdb/log/automation.log | grep 'MiqAeEvent.build_evm_event' |"
#             " grep 'event=<\"vm_poweroff\">' | grep 'id: {}'".format(vm.api.object.id)
#             # not guid, but the ID
#         )
#         if result.failed:  # Nothing found, so shortcut
#             return False
#         found = [event for event in result.output.strip().split("\n") if len(event) > 0]
#         if not found:
#             return False
#         else:
#             logger.info("Found event: `%s`", event[-1].strip())
#             return True
#     wait_for(search_logs, num_sec=180, message="log search")


# Purely custom actions
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_tag(request, vm, vm_off, policy_for_testing, appliance):
    """ Tests action tag

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    if any(tag.category.display_name == "Service Level" and tag.display_name == "Gold"
           for tag in vm.crud.get_tags()):
        vm.crud.remove_tag("Service Level", "Gold")

    tag_assign_action = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Service Level", "Gold")}
    )
    policy_for_testing.assign_actions_to_event("VM Power On", [tag_assign_action])

    @request.addfinalizer
    def finalize():
        policy_for_testing.assign_events()
        tag_assign_action.delete()

    vm.mgmt.start()
    try:
        wait_for(
            lambda: any(tag.category.display_name == "Service Level" and tag.display_name == "Gold"
                        for tag in vm.crud.get_tags()),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not assigned!")


@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_untag(request, vm, vm_off, policy_for_testing, appliance, tag):
    """ Tests action untag

    Metadata:
        test_flag: actions, provision

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: Control
    """
    if not any(vm_tag.category.display_name == tag.category.display_name and
               vm_tag.display_name == tag.display_name
               for vm_tag in vm.crud.get_tags()):
        vm.crud.add_tag(tag)

    @request.addfinalizer
    def _remove_tag():
        if any(vm_tag.category.display_name == tag.category.display_name and
               vm_tag.display_name == tag.display_name
               for vm_tag in vm.crud.get_tags()):
            vm.crud.remove_tag(tag)

    tag_unassign_action = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Remove Tags",
        action_values={"remove_tag": [tag.category.display_name]}
    )
    policy_for_testing.assign_actions_to_event("VM Power On", [tag_unassign_action])

    @request.addfinalizer
    def finalize():
        policy_for_testing.assign_events()
        tag_unassign_action.delete()

    vm.mgmt.start()
    try:

        wait_for(
            lambda: not any(vm_tag.category.display_name == tag.category.display_name and
                            vm_tag.display_name == tag.display_name
                            for vm_tag in vm.crud.get_tags()),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not unassigned!")


@pytest.mark.provider([VMwareProvider], scope="module")
@pytest.mark.meta(blockers=[BZ(1685201)])
def test_action_cancel_clone(appliance, request, provider, vm_name, vm_big, policy_for_testing,
        compliance_policy):
    """This test checks if 'Cancel vCenter task' action works.
    For this test we need big template otherwise CFME won't have enough time
    to cancel the task https://bugzilla.redhat.com/show_bug.cgi?id=1383372#c9

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control
    """
    with update(policy_for_testing):
        policy_for_testing.scope = (
            "fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_big.name))
    with update(compliance_policy):
        compliance_policy.scope = (
            "fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_big.name))
    policy_for_testing.assign_events("VM Clone Start")
    policy_for_testing.assign_actions_to_event(
        "VM Clone Start", ["Cancel vCenter Task"])
    clone_vm_name = "{}-clone".format(vm_big.name)

    @request.addfinalizer
    def finalize():
        policy_for_testing.assign_events()
        with update(policy_for_testing):
            policy_for_testing.scope = (
                "fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name))
        with update(compliance_policy):
            compliance_policy.scope = (
                "fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name))
        collection = provider.appliance.provider_based_collection(provider)
        collection.instantiate(clone_vm_name, provider).cleanup_on_provider()

    vm_big.crud.clone_vm(fauxfactory.gen_email(), "first", "last", clone_vm_name, "VMware")
    request_description = clone_vm_name
    clone_request = appliance.collections.requests.instantiate(description=request_description,
                                                               partial_check=True)
    clone_request.wait_for_request(method='ui')
    assert clone_request.status == "Error"


@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider],
    scope="module"
)
def test_action_check_compliance(request, provider, vm, vm_name, policy_for_testing,
        compliance_policy, compliance_condition, tag):
    """Tests action "Check Host or VM Compliance". Policy profile should have control and compliance
    policies. Control policy initiates compliance check and compliance policy determines is the vm
    compliant or not. After reloading vm details screen the compliance status should be changed.

    Metadata:
        test_flag: policy

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control
    """
    compliance_policy.assign_conditions(compliance_condition)
    if any(vm_tag.category.display_name == tag.category.display_name and
           vm_tag.display_name == tag.display_name
           for vm_tag in vm.crud.get_tags()):
        vm.crud.remove_tag(tag)

    @request.addfinalizer
    def _remove_tag():
        compliance_policy.assign_conditions()
        if any(vm_tag.category.display_name == tag.category.display_name and
               vm_tag.display_name == tag.display_name
               for vm_tag in vm.crud.get_tags()):
            vm.crud.remove_tag(tag)

    policy_for_testing.assign_actions_to_event("Tag Complete", ["Check Host or VM Compliance"])
    request.addfinalizer(policy_for_testing.assign_events)
    vm.crud.add_tag(tag)
    view = navigate_to(vm.crud, "Details")
    view.toolbar.reload.click()
    assert vm.crud.compliant
