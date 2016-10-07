# -*- coding: utf-8 -*-
""" Tests used to check whether assigned actions really do what they're supposed to do.

Required YAML keys:
    * Provider must have hostname (not amazon)
    * Provider must have section provisioning/template (otherwise test will be skipped)
    * RHEV-M provider must have provisioning/vlan specified, otherwise the test fails on provis.
    * There should be a 'datastores_not_for_provision' in the root, being a list of datastores that
        should not be used for tagging for provisioning. If not present,
        nothing terrible happens, but provisioning can be then assigned to a datastore that does not
        work (iso datastore or whatever), therefore failing the provision.
"""
import fauxfactory
import pytest

import mgmtsystem

from cfme.control import explorer
from cfme.configure import tasks
from cfme.infrastructure import host
from cfme.web_ui import tabstrip as tabs, toolbar as tb
from datetime import datetime
from utils import testgen
from utils.blockers import BZ
from utils.conf import cfme_data
from utils.log import logger
from utils.version import current_version, pick, LOWEST
from utils.wait import wait_for, TimedOutError
from cfme import test_requirements


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.all_providers(metafunc)

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if args["provider"].type in {"scvmm"}:
            continue

        if ((metafunc.function is test_action_create_snapshot_and_delete_last)
            or
            (metafunc.function is test_action_create_snapshots_and_delete_them)) \
                and args['provider'].type in {"rhevm", "openstack", "ec2"}:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(blockers=[
        BZ(
            1149128,
            unblock=lambda provider: not isinstance(provider.mgmt, mgmtsystem.scvmm.SCVMMSystem))
    ]),
    pytest.mark.meta(server_roles="+automate +smartproxy +smartstate"),
    pytest.mark.tier(2),
    test_requirements.control
]


def get_vm_object(vm_name):
    """Looks up the CFME database for the VM.

    Args:
        vm_name: VM name

    Returns:
        If found, :py:class:`utils.api.Entity`
        If not, `None`
    """
    try:
        return pytest.store.current_appliance.rest_api.collections.vms.find_by(name=vm_name)[0]
    except IndexError:
        return None


@pytest.fixture(scope="module")
def vm_name(provider):
    return "long-test_act-{}-{}".format(provider.key, fauxfactory.gen_alpha().lower())


def set_host_credentials(request, provider, vm):
    # Add credentials to host
    host_name = vm.api.host.name
    test_host = host.Host(name=host_name)

    host_list = cfme_data.get('management_systems', {})[vm._prov.key].get('hosts', [])
    host_data = [x for x in host_list if x.name == host_name][0]

    if not test_host.has_valid_credentials:
        test_host.update(
            updates={'credentials': host.get_credentials_from_config(host_data['credentials'])},
            validate_credentials=True
        )

    # Remove creds after test
    @request.addfinalizer
    def _host_remove_creds():
        test_host.update(
            updates={'credentials': host.Host.Credential(
                principal="", secret="", verify_secret="")},
            validate_credentials=False
        )


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
    roles["smartproxy"] = True
    roles["smartstate"] = True
    configuration.set_server_roles(**roles)
    yield
    configuration.set_server_roles(**old_roles)


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
        pytest.fail("CFME did not power on the VM {}".format(vm.name))


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
        pytest.fail("CFME did not power off the VM {}".format(vm.name))


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
        pytest.fail("CFME did not suspend the VM {}".format(vm.name))


@pytest.mark.meta(blockers=[1142875])
def test_action_prevent_event(request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
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


@pytest.mark.meta(blockers=[1333566])
def test_action_create_snapshot_and_delete_last(
        request, assign_policy_for_testing, vm, vm_on, vm_crud_refresh):
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
    snapshot_create_action = explorer.Action(
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
    vm_crud_refresh()
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


@pytest.mark.meta(blockers=[1333566])
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
        vm_crud_refresh()
        wait_for(lambda: vm.crud.total_snapshots > snapshots_before, num_sec=800,
                 message="wait for snapshot %d to appear" % (n + 1), delay=5)
        assert vm.crud.current_snapshot_name == snapshot_name
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
    wait_for(lambda: vm.crud.total_snapshots == 0, num_sec=800,
             message="wait for snapshots to be deleted", delay=5)


def test_action_initiate_smartstate_analysis(
        request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
    """ This test tests actions 'Initiate SmartState Analysis for VM'.

    This test sets the policy that it analyses VM after it's powered on. Then it checks whether
    that really happened.

    Metadata:
        test_flag: actions, provision
    """
    # Set host credentials for VMWare
    if isinstance(vm.provider, mgmtsystem.virtualcenter.VMWareSystem):
        set_host_credentials(request, vm.provider, vm)

    # Set up the policy and prepare finalizer
    assign_policy_for_testing.assign_actions_to_event("VM Power On",
                                                      ["Initiate SmartState Analysis for VM"])
    request.addfinalizer(lambda: assign_policy_for_testing.assign_events())
    switched_on = datetime.utcnow()
    # Start the VM
    vm.crud.power_control_from_cfme(option=vm.crud.POWER_ON, cancel=False, from_details=True)

    # Wait for VM being tried analysed by CFME
    def wait_analysis_tried():
        if current_version() > "5.5":
            vm.api.reload()
        try:
            return vm.api.last_scan_attempt_on.replace(tzinfo=None) >= switched_on
        except AttributeError:
            return False
    try:
        wait_for(wait_analysis_tried, num_sec=360, message="wait for analysis attempt", delay=5)
    except TimedOutError:
        pytest.fail("CFME did not even try analysing the VM {}".format(vm.name))

    # Check that analyse job has appeared in the list
    # Wait for the task to finish
    @pytest.wait_for(delay=15, timeout="8m", fail_func=lambda: tb.select('Reload'))
    def is_vm_analysis_finished():
        """ Check if analysis is finished - if not, reload page
        """
        tab_name = pick({
            LOWEST: "All VM Analysis Tasks",
            '5.6': "All VM and Container Analysis Tasks",
        })
        if not pytest.sel.is_displayed(tasks.tasks_table) or \
           not tabs.is_tab_selected(tab_name):
            pytest.sel.force_navigate('tasks_all_vm')
        vm_analysis_finished = tasks.tasks_table.find_row_by_cells({
            'task_name': "Scan from Vm {}".format(vm.name),
            'state': 'finished'
        })
        return vm_analysis_finished is not None

    # Wait for VM analysis to finish
    def wait_analysis_finished():
        if current_version() > "5.5":
            vm.api.reload()
        try:
            return vm.api.last_scan_on.replace(tzinfo=None) >= switched_on
        except AttributeError:
            return False
    try:
        wait_for(wait_analysis_finished, num_sec=600,
                 message="wait for analysis finished", delay=60)
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
def test_action_tag(request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
    """ Tests action tag

    Metadata:
        test_flag: actions, provision
    """
    if any(tag.category.display_name == "Service Level" and tag.display_name == "Gold"
           for tag in vm.crud.get_tags()):
        vm.crud.remove_tag(("Service Level", "Gold"))

    tag_assign_action = explorer.Action(
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
    vm_crud_refresh()
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
def test_action_untag(request, assign_policy_for_testing, vm, vm_off, vm_crud_refresh):
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

    tag_unassign_action = explorer.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Remove Tags",
        action_values={"cat_service_level": True}
    )
    assign_policy_for_testing.assign_actions_to_event("VM Power On", [tag_unassign_action])

    @request.addfinalizer
    def finalize():
        assign_policy_for_testing.assign_events()
        tag_unassign_action.delete()

    vm.start_vm()
    vm_crud_refresh()
    try:

        wait_for(
            lambda: not any(tag.category.display_name == "Service Level" and
                            tag.display_name == "Gold" for tag in vm.crud.get_tags()),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not unassigned!")
