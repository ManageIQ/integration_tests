# -*- coding: utf-8 -*-
""" Tests used to check whether assigned actions really do what they're supposed to do.

Required YAML keys:
    * Provider must have hostname (not amazon)
    * Provider must have section provisioning/template (otherwise test will be skipped)
    * RHEV-M provider must have provisioning/vlan specified, otherwise the test fails on provis.
    * There should be a 'datastores_not_for_provision' in the root, being a list of datastores that
        should not be used for tagging for provisioning (used by miq_soap.py). If not present,
        nothing terrible happens, but provisioning can be then assigned to a datastore that does not
        work (iso datastore or whatever), therefore failing the provision.
"""
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.control import explorer
from cfme.exceptions import FlashMessageException
from cfme.infrastructure.provider import RHEVMProvider
from datetime import datetime
from functools import partial
from utils import mgmt_system, testgen
from utils.blockers import BZ
from utils.db import cfmedb
from utils.log import logger
from utils.miq_soap import MiqVM
from utils.providers import setup_provider
from utils.virtual_machines import deploy_template
from utils.wait import wait_for, TimedOutError
from utils.pretty import Pretty


class VMWrapper(Pretty):
    """This class binds a provider_mgmt object with VM name. Useful for on/off operation"""
    __slots__ = ("_mgmt", "_vm", "soap")
    pretty_attrs = ['_vm', '_mgmt']

    def __init__(self, provider_mgmt, vm_name, soap):
        self._mgmt = provider_mgmt
        self._vm = vm_name
        self.soap = soap

    @property
    def name(self):
        return self._vm

    @property
    def provider(self):
        return self._mgmt

    def __getattr__(self, key):
        """Creates partial functions proxying to mgmt_system.<function_name>(vm_name)"""
        func = getattr(self._mgmt, key)
        return partial(func, self._vm)


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.all_providers(metafunc,
        'small_template', scope="module", template_location=["small_template"])

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if args["provider"].type in {"scvmm"}:
            continue

        if ((metafunc.function is test_action_create_snapshot_and_delete_last)
            or
            (metafunc.function is test_action_create_snapshots_and_delete_them)) \
                and isinstance(args['provider'], RHEVMProvider):
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(blockers=[
        BZ(
            1149128,
            unblock=lambda provider: not isinstance(provider.mgmt, mgmt_system.SCVMMSystem))
    ])
]


def get_vm_object(vm_name):
    """Looks up the CFME database for the VM.

    Args:
        vm_name: VM name
    Returns:
        If found, :py:class:`utils.miq_soap.MiqVM`. If not, `None`
    """
    vm_table = cfmedb()['vms']
    for vm in cfmedb().session.query(vm_table.name, vm_table.guid)\
            .filter(vm_table.template == False):  # NOQA
        # Previous line is ok, if you change it to `is`, it won't work!
        if vm.name == vm_name:
            return MiqVM(vm.guid)
    else:
        return None


@pytest.fixture(scope="module")
def vm_name(provider):
    return "test_act-{}-{}".format(provider.key, fauxfactory.gen_alpha().lower())


@pytest.fixture(scope="module")
def vm(request, provider, small_template, vm_name):
    try:
        setup_provider(provider.key)
    except FlashMessageException as e:
        e.skip_and_log("Provider failed to set up")

    if isinstance(provider.mgmt, mgmt_system.RHEVMSystem):
        kwargs = {"cluster": provider.data["default_cluster"]}
    elif isinstance(provider.mgmt, mgmt_system.VMWareSystem):
        kwargs = {}
    elif isinstance(provider.mgmt, mgmt_system.SCVMMSystem):
        kwargs = {
            "host_group": provider.data.get("provisioning", {}).get("host_group", "All Hosts")}
    else:
        kwargs = {}

    try:
        deploy_template(
            provider.key,
            vm_name,
            template_name=small_template,
            allow_skip="default",
            power_on=True,
            **kwargs
        )
    except TimedOutError as e:
        logger.exception(e)
        try:
            provider.mgmt.delete_vm(vm_name)
        except TimedOutError:
            logger.warning("Could not delete VM {}!".format(vm_name))
        finally:
            # If this happened, we should skip all tests from this provider in this module
            pytest.skip("{} is quite likely overloaded! Check its status!\n{}: {}".format(
                provider.key, type(e).__name__, str(e)))

    def finalize():
        """if getting SOAP object failed, we would not get the VM deleted! So explicit teardown."""
        logger.info("Shutting down VM with name {}".format(vm_name))
        if provider.mgmt.is_vm_suspended(vm_name):
            logger.info("Powering up VM {} to shut it down correctly.".format(vm_name))
            provider.mgmt.start_vm(vm_name)
        if provider.mgmt.is_vm_running(vm_name):
            logger.info("Powering off VM {}".format(vm_name))
            provider.mgmt.stop_vm(vm_name)
        if provider.mgmt.does_vm_exist(vm_name):
            logger.info("Deleting VM {} in {}".format(vm_name, provider.mgmt.__class__.__name__))
            provider.mgmt.delete_vm(vm_name)
    request.addfinalizer(finalize)

    # Make it appear in the provider
    provider.refresh_provider_relationships()

    # Get the SOAP object
    soap = wait_for(
        lambda: get_vm_object(vm_name),
        message="VM object {} appears in CFME".format(vm_name),
        fail_condition=None,
        num_sec=600,
        delay=15,
    )[0]

    return VMWrapper(provider.mgmt, vm_name, soap)


@pytest.fixture(scope="module")
def name_suffix():
    return fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def policy_name(name_suffix):
    return "action_testing: policy {}".format(name_suffix)


@pytest.fixture(scope="module")
def policy_profile_name(name_suffix):
    return "action_testing: policy profile {}".format(name_suffix)


@pytest.yield_fixture(scope="module")
def automate_role_set(request):
    """ Sets the Automate role that the VM can be provisioned.

    Sets the Automate role state back when finished the module tests.
    """
    from cfme.configure import configuration
    roles = configuration.get_server_roles()
    old_roles = dict(roles)
    roles["automate"] = True
    configuration.set_server_roles(**roles)
    yield
    configuration.set_server_roles(**old_roles)


@pytest.fixture(scope="module")
def vm_crud(vm_name, provider):
    return VM.factory(vm_name, provider)


@pytest.fixture(scope="function")
def vm_on(vm, vm_crud):
    """ Ensures that the VM is on when the control goes to the test."""
    vm.wait_vm_steady()
    if not vm.is_vm_running():
        vm.start_vm()
        vm.wait_vm_running()
    # Make sure the state is consistent
    vm_crud.refresh_relationships(from_details=True)
    vm_crud.wait_for_vm_state_change(desired_state=vm_crud.STATE_ON, from_details=True)
    return vm


@pytest.fixture(scope="function")
def vm_off(vm, vm_crud):
    """ Ensures that the VM is off when the control goes to the test."""
    vm.wait_vm_steady()
    if vm.is_vm_suspended():
        vm.start_vm()
        vm.wait_vm_running()
    if not vm.is_vm_stopped():
        vm.stop_vm()
        vm.wait_vm_stopped()
    # Make sure the state is consistent
    vm_crud.refresh_relationships(from_details=True)
    vm_crud.wait_for_vm_state_change(desired_state=vm_crud.STATE_OFF, from_details=True)
    return vm


@pytest.fixture(scope="function")
def vm_crud_refresh(vm_crud, provider):
    """Refreshes the VM if that is needed for the provider."""
    if provider.type in {"ec2"}:
        return lambda: vm_crud.refresh_relationships(from_details=True)
    else:
        return lambda: None


@pytest.yield_fixture(scope="module")
def policy_for_testing(automate_role_set, vm, policy_name, policy_profile_name, provider):
    """ Takes care of setting the appliance up for testing """
    policy = explorer.VMControlPolicy(
        policy_name,
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm.name)
    )
    policy.create()
    policy_profile = explorer.PolicyProfile(policy_profile_name, policies=[policy])
    policy_profile.create()
    yield policy
    policy_profile.delete()
    policy.delete()


@pytest.yield_fixture(scope="module")
def assign_policy_for_testing(vm, policy_for_testing, provider, policy_profile_name):
    provider.assign_policy_profiles(policy_profile_name)
    yield policy_for_testing
    provider.unassign_policy_profiles(policy_profile_name)


def test_action_start_virtual_machine_after_stopping(
        request, assign_policy_for_testing, vm, vm_on, vm_crud_refresh):
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
    vm_crud_refresh()
    # Wait for VM powered on by CFME
    try:
        wait_for(vm.is_vm_running, num_sec=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power on the VM %s" % vm.name)


def test_action_stop_virtual_machine_after_starting(
        request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
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
    vm_crud_refresh()
    # Wait for VM powered off by CFME
    try:
        wait_for(vm.is_vm_stopped, num_sec=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power off the VM %s" % vm.name)


def test_action_suspend_virtual_machine_after_starting(
        request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
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
    vm_crud_refresh()
    # Wait for VM be suspended by CFME
    try:
        wait_for(vm.is_vm_suspended, num_sec=600, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not suspend the VM %s" % vm.name)


@pytest.mark.meta(blockers=[1142875])
def test_action_prevent_event(
        request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
    """ This test tests action 'Prevent current event from proceeding'

    Must be done with SOAP.

    This test sets the policy that it prevents powering the VM up. Then the vm is powered up
    and then it waits that VM does not come alive.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On Request",
                                                      ["Prevent current event from proceeding"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Request VM's start
    vm.soap.power_on()   # THROUGH SOAP, because through mgmt_sys would not generate req event.
    try:
        wait_for(vm.is_vm_running, num_sec=600, delay=5)
    except TimedOutError:
        pass  # VM did not start, so that's what we want
    else:
        pytest.fail("CFME did not prevent starting of the VM %s" % vm.name)


def test_action_power_on_logged(
        request, assign_policy_for_testing, vm, vm_off, ssh_client, vm_crud_refresh):
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
    vm_crud_refresh()
    policy_desc = assign_policy_for_testing.description

    # Search the logs
    def search_logs():
        rc, stdout = ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/policy.log | grep '%s'" % policy_desc
        )
        if rc != 0:  # Nothing found, so shortcut
            return False
        for line in stdout.strip().split("\n"):
            if "Policy success" not in line:
                continue
            match_string = "policy: [%s], event: [VM Power On], entity name: [%s]" % (
                assign_policy_for_testing.description, vm.name
            )
            if match_string in line:
                logger.info("Found corresponding log message: %s" % line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=180, message="log search")


def test_action_power_on_audit(
        request, assign_policy_for_testing, vm, vm_off, ssh_client, vm_crud_refresh):
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
    vm_crud_refresh()
    policy_desc = assign_policy_for_testing.description

    # Search the logs
    def search_logs():
        rc, stdout = ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/audit.log | grep '%s'" % policy_desc
        )
        if rc != 0:  # Nothing found, so shortcut
            return False
        for line in stdout.strip().split("\n"):
            if "Policy success" not in line or "MiqAction.action_audit" not in line:
                continue
            match_string = "policy: [%s], event: [VM Power On]" % (policy_desc)
            if match_string in line:
                logger.info("Found corresponding log message: %s" % line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=180, message="log search")


def test_action_create_snapshot_and_delete_last(
        request, assign_policy_for_testing, vm, vm_on, vm_crud_refresh):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete Most Recent Snapshot'.

    This test sets the policy that it makes snapshot of VM after it's powered off and when it is
    powered back on, it deletes the last snapshot.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    snapshot_name = fauxfactory.gen_alphanumeric()
    snapshot_create_action = explorer.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])
    assign_policy_for_testing.assign_actions_to_event("VM Power On",
                                                      ["Delete Most Recent Snapshot"])

    def finalize():
        assign_policy_for_testing.assign_events()
        snapshot_create_action.delete()
    request.addfinalizer(finalize)

    snapshots_before = vm.soap.ws_attributes["v_total_snapshots"]
    # Power off to invoke snapshot creation
    vm.stop_vm()
    vm_crud_refresh()
    wait_for(lambda: vm.soap.ws_attributes["v_total_snapshots"] > snapshots_before, num_sec=800,
             message="wait for snapshot appear", delay=5)
    assert vm.soap.ws_attributes["v_snapshot_newest_description"] == "Created by EVM Policy Action"
    assert vm.soap.ws_attributes["v_snapshot_newest_name"] == snapshot_name
    # Snapshot created and validated, so let's delete it
    snapshots_before = vm.soap.ws_attributes["v_total_snapshots"]
    # Power on to invoke last snapshot deletion
    vm.start_vm()
    wait_for(lambda: vm.soap.ws_attributes["v_total_snapshots"] < snapshots_before, num_sec=800,
             message="wait for snapshot deleted", delay=5)


def test_action_create_snapshots_and_delete_them(
        request, assign_policy_for_testing, vm, vm_on, vm_crud_refresh):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete all Snapshots'.

    This test sets the policy that it makes snapshot of VM after it's powered off and then it cycles
    several time that it generates a couple of snapshots. Then the 'Delete all Snapshots' is
    assigned to power on event, VM is powered on and it waits for all snapshots to disappear.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    snapshot_name = fauxfactory.gen_alphanumeric()
    snapshot_create_action = explorer.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])

    def finalize():
        assign_policy_for_testing.assign_events()
        snapshot_create_action.delete()
    request.addfinalizer(finalize)

    def create_one_snapshot(n):
        """
        Args:
            n: Sequential number of snapshot for logging.
        """
        # Power off to invoke snapshot creation
        snapshots_before = vm.soap.ws_attributes["v_total_snapshots"]
        vm.stop_vm()
        vm_crud_refresh()
        wait_for(lambda: vm.soap.ws_attributes["v_total_snapshots"] > snapshots_before, num_sec=800,
                 message="wait for snapshot %d to appear" % (n + 1), delay=5)
        assert vm.soap.ws_attributes["v_snapshot_newest_name"] == snapshot_name
        vm.start_vm()
        vm_crud_refresh()

    for i in range(4):
        create_one_snapshot(i)
    assign_policy_for_testing.assign_events()
    vm.stop_vm()
    vm_crud_refresh()
    assign_policy_for_testing.assign_actions_to_event("VM Power On", ["Delete all Snapshots"])
    # Power on to invoke all snapshots deletion
    vm.start_vm()
    vm_crud_refresh()
    wait_for(lambda: vm.soap.ws_attributes["v_total_snapshots"] == 0, num_sec=800,
             message="wait for snapshots to be deleted", delay=5)


@pytest.mark.uncollect()
def test_action_initiate_smartstate_analysis(
        request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
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
    # Remember the time
    switched_on = datetime.now()
    # Start the VM
    vm.start_vm()
    vm_crud_refresh()

    # Wait for VM being tried analysed by CFME
    def wait_analysis_tried():
        t = vm.soap.last_scan_attempt_on
        return False if t is None else t >= switched_on
    try:
        wait_for(wait_analysis_tried, num_sec=90, message="wait for analysis attempt", delay=5)
    except TimedOutError:
        pytest.fail("CFME did not even try analysing the VM %s" % vm.name)

    # Wait for VM analysis to finish
    def wait_analysis_finished():
        t = vm.soap.last_scan_on
        return False if t is None else t >= switched_on
    try:
        wait_for(wait_analysis_finished, num_sec=180, message="wait for analysis finished", delay=5)
    except TimedOutError:
        pytest.fail("CFME did not analyse the VM %s" % vm.name)


def test_action_raise_automation_event(
        request, assign_policy_for_testing, vm, vm_on, ssh_client, vm_crud_refresh):
    """ This test tests actions 'Raise Automation Event'.

    This test sets the policy that it raises an automation event VM after it's powered on.
    Then it checks logs whether that really happened.

    Metadata:
        test_flag: actions, provision
    """
    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power Off", ["Raise Automation Event"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    # Start the VM
    vm.stop_vm()
    vm_crud_refresh()

    # Search the logs
    def search_logs():
        rc, stdout = ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/automation.log | grep 'MiqAeEvent.build_evm_event' |"
            " grep 'event=<\"vm_poweroff\">' | grep 'id: %s'" % vm.soap.object.id
            # not guid, but the ID
        )
        if rc != 0:  # Nothing found, so shortcut
            return False
        found = [event for event in stdout.strip().split("\n") if len(event) > 0]
        if not found:
            return False
        else:
            logger.info("Found event: `%s`" % event[-1].strip())
            return True
    wait_for(search_logs, num_sec=180, message="log search")


# Purely custom actions
def test_action_tag(request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
    """ Tests action tag

    Metadata:
        test_flag: actions, provision
    """
    tag_assign_action = explorer.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Service Level", "Gold")}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power On", [tag_assign_action])

    def finalize():
        assign_policy_for_testing.assign_events()
        tag_assign_action.delete()
    request.addfinalizer(finalize)

    vm.start_vm()
    vm_crud_refresh()
    try:
        wait_for(
            lambda: any(
                [tag.category == "service_level" and tag.tag_name == "gold" for tag in vm.soap.tags]
            ),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not assigned!")


@pytest.mark.meta(blockers=[1205496])
def test_action_untag(request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
    """ Tests action untag

    Metadata:
        test_flag: actions, provision
    """
    tag_unassign_action = explorer.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Remove Tags",
        action_values={"cat_service_level": True}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power On", [tag_unassign_action])

    def finalize():
        assign_policy_for_testing.assign_events()
        tag_unassign_action.delete()
    request.addfinalizer(finalize)

    vm.start_vm()
    vm_crud_refresh()
    try:
        wait_for(
            lambda: not any(
                [tag.category == "service_level" and tag.tag_name == "gold" for tag in vm.soap.tags]
            ),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not unassigned!")
