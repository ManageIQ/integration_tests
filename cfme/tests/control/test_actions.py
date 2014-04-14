#!/usr/bin/env python2
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

import pytest
from cfme.control import explorer
from cfme.infrastructure import provider
from datetime import datetime
from utils.conf import cfme_data
from utils.log import logger
from utils.miq_soap import MiqVM
from utils.providers import list_infra_providers
from utils.randomness import generate_random_string
from utils.wait import wait_for, TimedOutError

pytestmark = [pytest.mark.usefixtures("setup_infrastructure_providers")]


@pytest.fixture(scope="module", params=list_infra_providers())
def provider_id(request):
    """ This fixture ensures parametrization across multiple providers. Infra so far.
    """
    return request.param


@pytest.fixture(scope="module")
def provider_template(provider_id):
    template = cfme_data["management_systems"][provider_id]\
        .get("provisioning", {})\
        .get("template", None)
    if template is None:
        pytest.skip("No provisioning template for %s" % provider_id)
    else:
        return template


@pytest.fixture(scope="module")
def provider_vlan(provider_id):
    return cfme_data["management_systems"][provider_id].get("provisioning", {}).get("vlan", None)


@pytest.fixture(scope="module")
def name_suffix():
    return generate_random_string()


@pytest.fixture(scope="module")
def policy_name(name_suffix):
    return "action_testing: policy %s" % name_suffix


@pytest.fixture(scope="module")
def policy_profile_name(name_suffix):
    return "action_testing: policy profile %s" % name_suffix


@pytest.fixture(scope="module")
def vm_name(name_suffix, provider_id):
    return "test_default_actions-{}-{}".format(provider_id, name_suffix)


@pytest.fixture(scope="module")
def automate_role_set():
    """ Sets the Automate role that the VM can be provisioned.

    Sets the Automate role state back when finished the module tests.
    """
    from cfme.configure import configuration
    roles = configuration.get_server_roles()
    roles["automate"] = True
    configuration.set_server_roles(**roles)


@pytest.yield_fixture(scope="module")
def vm(request, automate_role_set, vm_name, provider_id, provider_template, provider_vlan):
    """ Provides a provisioned VM instance and ensures it is deleted after testing.

    It is parametrized with template names.
    """
    logger.info("Provisioning VM with name %s" % vm_name)
    try:
        vm = MiqVM.provision_from_template(provider_template, vm_name,
                                           wait_min=7, vlan=provider_vlan)
    except Exception as e:
        if "Unable to access file" in e.message:
            logger.info("First attempt to clone VM failed (%s), trying again" % e.message)
            vm = MiqVM.provision_from_template(provider_template, vm_name,
                                               wait_min=7, vlan=provider_vlan)
        else:
            raise
    logger.info("VM with name %s provisioned" % vm_name)
    vm_provider = vm.provider.direct_connection
    yield vm
    logger.info("Shutting down VM with name %s" % vm_name)
    if vm_provider.is_vm_suspended(vm_name):
        logger.info("Powering up VM %s to shut it down" % vm_name)  # This should be done by miqsoap
        vm_provider.start_vm(vm_name)
        wait_for(lambda: vm_provider.is_vm_running(vm_name), num_sec=70, delay=5)
    if vm_provider.is_vm_running(vm_name):
        logger.info("Powering off VM %s" % vm_name)
        vm_provider.stop_vm(vm_name)
        wait_for(lambda: vm_provider.is_vm_stopped(vm_name), num_sec=70, delay=5)
    logger.info("Deleting VM with name %s" % vm_name)
    vm.delete()  # CFME delete
    logger.info("VM with name %s deleted in VMDB, now it's time to check the provider" % vm_name)
    if vm_provider.does_vm_exist(vm_name):
        logger.info("Deleting VM %s in %s" % (vm_name, vm_provider.__class__.__name__))
        vm_provider.delete_vm(vm_name)
        wait_for(
            lambda: not vm_provider.does_vm_exist(vm_name),
            num_sec=60, message="check the VM %s does not exist any more" % vm_name, delay=5
        )


@pytest.fixture(scope="module")
def vm_provider_conn(vm):
    """ Provides the provider connection object for the provider of the VM.
    """
    return vm.provider.direct_connection


# "PARTIAL" functions provided as fixtures. They always correspond to current `vm` object
@pytest.fixture(scope="module")
def vm_start_func(vm_name, vm_provider_conn):
    return lambda: vm_provider_conn.start_vm(vm_name)


@pytest.fixture(scope="module")
def vm_stop_func(vm_name, vm_provider_conn):
    return lambda: vm_provider_conn.stop_vm(vm_name)


@pytest.fixture(scope="module")
def vm_is_on_func(vm_name, vm_provider_conn):
    return lambda: vm_provider_conn.is_vm_running(vm_name)


@pytest.fixture(scope="module")
def vm_is_off_func(vm_name, vm_provider_conn):
    return lambda: vm_provider_conn.is_vm_stopped(vm_name)


@pytest.fixture(scope="module")
def vm_is_suspended_func(vm_name, vm_provider_conn):
    return lambda: vm_provider_conn.is_vm_suspended(vm_name)


@pytest.fixture(scope="function")
def vm_on(vm_start_func, vm_is_on_func, vm_name):
    """ Ensures that the VM is on when the control goes to the test.
    """
    if not vm_is_on_func():
        logger.info("Powering on %s" % vm_name)
        vm_start_func()
        wait_for(vm_is_on_func, num_sec=70, delay=5)


@pytest.fixture(scope="function")
def vm_off(
        vm_stop_func, vm_is_off_func, vm_is_suspended_func, vm_start_func, vm_is_on_func, vm_name):
    """ Ensures that the VM is off when the control goes to the test.
    """
    if not vm_is_off_func():
        if vm_is_suspended_func():
            logger.info("Powering on %s from suspend to power off without exception" % vm_name)
            vm_start_func()
            wait_for(vm_is_on_func, num_sec=60, delay=5)
        logger.info("Powering off %s" % vm_name)
        vm_stop_func()
        wait_for(vm_is_off_func, num_sec=60, delay=5)


@pytest.yield_fixture(scope="module")
def policy_for_testing(policy_name, policy_profile_name, provider_id, vm_name):
    """ Takes care of setting the appliance up for testing """
    policy = explorer.VMControlPolicy(
        policy_name,
        scope="fill_field(VM and Instance : Name, INCLUDES, %s)" % vm_name
    )
    policy.create()
    policy_profile = explorer.PolicyProfile(policy_profile_name, policies=[policy])
    policy_profile.create()
    prov = provider.get_from_config(provider_id)
    prov.assign_policy_profiles(policy_profile_name)
    yield policy
    prov.unassign_policy_profiles(policy_profile_name)
    policy_profile.delete()
    policy.delete()


def test_action_start_virtual_machine_after_stopping(
        request, policy_for_testing, vm, vm_on, vm_stop_func, vm_is_off_func, vm_is_on_func):
    """ This test tests action 'Start Virtual Machine'

    This test sets the policy that it turns on the VM when it is turned off
    (https://www.youtube.com/watch?v=UOn4gxj2Dso), then turns the VM off and waits for it coming
    back alive.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power Off", ["Start Virtual Machine"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Stop the VM
    vm_stop_func()
    try:
        wait_for(vm_is_off_func, num_sec=60, delay=5)
    except TimedOutError:
        pass
    # Wait for VM powered on by CFME
    try:
        wait_for(vm_is_on_func, num_sec=180, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power on the VM %s" % vm.name)


def test_action_stop_virtual_machine_after_starting(
        request, policy_for_testing, vm, vm_off, vm_start_func, vm_is_on_func, vm_is_off_func):
    """ This test tests action 'Stop Virtual Machine'

    This test sets the policy that it turns off the VM when it is turned on
    (https://www.youtube.com/watch?v=UOn4gxj2Dso), then turns the VM on and waits for it coming
    back off.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Stop Virtual Machine"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Start the VM
    vm_start_func()
    try:
        wait_for(vm_is_on_func, num_sec=60, delay=5)
    except TimedOutError:
        pass
    # Wait for VM powered off by CFME
    try:
        wait_for(vm_is_off_func, num_sec=180, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power off the VM %s" % vm.name)


def test_action_suspend_virtual_machine_after_starting(
        request, policy_for_testing, vm, vm_off, vm_name, vm_start_func, vm_is_on_func,
        vm_is_suspended_func):
    """ This test tests action 'Suspend Virtual Machine'

    This test sets the policy that it suspends the VM when it's turned on. Then it powers on the vm,
    waits for it becoming alive and then it waits for the VM being suspended.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Suspend Virtual Machine"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Start the VM
    vm_start_func()
    # Wait for VM be suspended by CFME
    try:
        wait_for(vm_is_suspended_func, num_sec=180, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not suspend the VM %s" % vm_name)


def test_action_prevent_event(
        request, policy_for_testing, vm, vm_off, vm_is_on_func, vm_name):
    """ This test tests action 'Prevent current event from proceeding'

    Must be done with SOAP.

    This test sets the policy that it prevents powering the VM up. Then the vm is powered up
    and then it waits that VM does not come alive.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On Request",
                                               ["Prevent current event from proceeding"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Request VM's start
    vm.power_on()   # THROUGH SOAP, because through mgmt_sys would not generate req event.
    try:
        wait_for(vm_is_on_func, num_sec=180, delay=5)
    except TimedOutError:
        pass  # VM did not start, so that's what we want
    else:
        pytest.fail("CFME did not prevent starting of the VM %s" % vm_name)


def test_action_power_on_logged(
        request, policy_for_testing, vm, vm_off, ssh_client, vm_name, vm_start_func, vm_is_on_func):
    """ This test tests action 'Generate log message'.

    This test sets the policy that it logs powering on of the VM. Then it powers up the vm and
    checks whether logs contain message about that.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Generate log message"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Start the VM
    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)
    policy_desc = policy_for_testing.description

    # Search the logs
    def search_logs():
        rc, stdout = ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/policy.log | grep '%s'" % policy_desc
        )
        assert rc == 0, "Grep'ing policy.log failed!"
        assert len(stdout.strip()) > 0, "No result of grep!"
        for line in stdout.strip().split("\n"):
            if not "Policy success" in line:
                continue
            match_string = "policy: [%s], event: [VM Power On], entity name: [%s]" % (
                policy_for_testing.description, vm_name
            )
            if match_string in line:
                logger.info("Found corresponding log message: %s" % line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=60, message="log search")


def test_action_power_on_audit(
        request, policy_for_testing, vm, vm_off, ssh_client, vm_start_func, vm_is_on_func):
    """ This test tests action 'Generate Audit Event'.

    This test sets the policy that it logs powering on of the VM. Then it powers up the vm and
    checks whether audit logs contain message about that.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Generate Audit Event"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Start the VM
    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)
    policy_desc = policy_for_testing.description

    # Search the logs
    def search_logs():
        rc, stdout = ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/audit.log | grep '%s'" % policy_desc
        )
        assert rc == 0, "Grep'ing audit.log failed!"
        for line in stdout.strip().split("\n"):
            if not "Policy success" in line or "MiqAction.action_audit" not in line:
                continue
            match_string = "policy: [%s], event: [VM Power On]" % (policy_desc)
            if match_string in line:
                logger.info("Found corresponding log message: %s" % line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=60, message="log search")


def test_action_create_snapshot_and_delete_last(
        request, policy_for_testing, vm, vm_on, vm_stop_func, vm_is_off_func, vm_start_func,
        vm_is_on_func):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete Most Recent Snapshot'.

    This test sets the policy that it makes snapshot of VM after it's powered off and when it is
    powered back on, it deletes the last snapshot.
    """
    # Set up the policy and prepare finalizer
    snapshot_name = generate_random_string()
    snapshot_create_action = explorer.Action(
        generate_random_string(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])
    policy_for_testing.assign_actions_to_event("VM Power On", ["Delete Most Recent Snapshot"])

    def finalize():
        policy_for_testing.assign_events()
        snapshot_create_action.delete()
    request.addfinalizer(finalize)

    snapshots_before = vm.ws_attributes["v_total_snapshots"]
    # Power off to invoke snapshot creation
    vm_stop_func()
    wait_for(vm_is_off_func, num_sec=90, delay=5)
    wait_for(lambda: vm.ws_attributes["v_total_snapshots"] > snapshots_before, num_sec=300,
        message="wait for snapshot appear", delay=5)
    assert vm.ws_attributes["v_snapshot_newest_description"] == "Created by EVM Policy Action"
    assert vm.ws_attributes["v_snapshot_newest_name"] == snapshot_name
    # Snapshot created and validated, so let's delete it
    snapshots_before = vm.ws_attributes["v_total_snapshots"]
    # Power on to invoke last snapshot deletion
    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)
    wait_for(lambda: vm.ws_attributes["v_total_snapshots"] < snapshots_before, num_sec=300,
        message="wait for snapshot deleted", delay=5)


def test_action_create_snapshots_and_delete_them(
        request, policy_for_testing, vm, vm_on, vm_start_func, vm_is_on_func, vm_stop_func,
        vm_is_off_func):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete all Snapshots'.

    This test sets the policy that it makes snapshot of VM after it's powered off and then it cycles
    several time that it generates a couple of snapshots. Then the 'Delete all Snapshots' is
    assigned to power on event, VM is powered on and it waits for all snapshots to disappear.
    """
    # Set up the policy and prepare finalizer
    snapshot_name = generate_random_string()
    snapshot_create_action = explorer.Action(
        generate_random_string(),
        action_type="Create a Snapshot",
        action_values={"snapshot_name": snapshot_name}
    )
    policy_for_testing.assign_actions_to_event("VM Power Off", [snapshot_create_action])

    def finalize():
        policy_for_testing.assign_events()
        snapshot_create_action.delete()
    request.addfinalizer(finalize)

    def create_one_snapshot(n):
        """
        Args:
            n: Sequential number of snapshot for logging.
        """
        # Power off to invoke snapshot creation
        snapshots_before = vm.ws_attributes["v_total_snapshots"]
        vm_stop_func()
        wait_for(vm_is_off_func, num_sec=90, delay=5)
        wait_for(lambda: vm.ws_attributes["v_total_snapshots"] > snapshots_before, num_sec=300,
            message="wait for snapshot %d to appear" % (n + 1), delay=5)
        assert vm.ws_attributes["v_snapshot_newest_name"] == snapshot_name
        vm_start_func()
        wait_for(vm_is_on_func, num_sec=90, delay=5)

    for i in range(4):
        create_one_snapshot(i)
    policy_for_testing.assign_events()
    vm_stop_func()
    policy_for_testing.assign_actions_to_event("VM Power On", ["Delete all Snapshots"])
    wait_for(vm_is_off_func, num_sec=90, delay=5)   # we can check it later here to speed up
    # Power on to invoke all snapshots deletion
    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)
    wait_for(lambda: vm.ws_attributes["v_total_snapshots"] == 0, num_sec=300,
        message="wait for snapshots to be deleted", delay=5)


@pytest.mark.skipif("True")
def test_action_initiate_smartstate_analysis(
        request, policy_for_testing, vm, vm_off, vm_start_func, vm_is_on_func):
    """ This test tests actions 'Initiate SmartState Analysis for VM'.

    This test sets the policy that it analyses VM after it's powered on. Then it checks whether
    that really happened.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On",
                                               ["Initiate SmartState Analysis for VM"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Remember the time
    switched_on = datetime.now()
    # Start the VM
    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)

    # Wait for VM being tried analysed by CFME
    def wait_analysis_tried():
        t = vm.last_scan_attempt_on
        return False if t is None else t >= switched_on
    try:
        wait_for(wait_analysis_tried, num_sec=90, message="wait for analysis attempt", delay=5)
    except TimedOutError:
        pytest.fail("CFME did not even try analysing the VM %s" % vm.name)

    # Wait for VM analysis to finish
    def wait_analysis_finished():
        t = vm.last_scan_on
        return False if t is None else t >= switched_on
    try:
        wait_for(wait_analysis_finished, num_sec=180, message="wait for analysis finished", delay=5)
    except TimedOutError:
        pytest.fail("CFME did not analyse the VM %s" % vm.name)


def test_action_raise_automation_event(
        request, policy_for_testing, vm, vm_off, ssh_client, vm_start_func, vm_is_on_func):
    """ This test tests actions 'Raise Automation Event'.

    This test sets the policy that it raises an automation event VM after it's powered on.
    Then it checks logs whether that really happened.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power On", ["Raise Automation Event"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Start the VM
    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)

    # Search the logs
    def search_logs():
        rc, stdout = ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/automation.log | grep 'vm_id=%s'" % vm.object.id
            # not guid, but the ID
        )
        assert rc == 0, "Grep'ing automation.log failed!"
        for line in stdout.strip().split("\n"):
            if not "Instantiating" in line:
                continue
            if "event_type=PowerOnVM_Task_Complete" in line:
                logger.info("Found corresponding log message: %s" % line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=80, message="log search")


# Purely custom actions
def test_action_tag(request, policy_for_testing, vm, vm_off, vm_start_func, vm_is_on_func):
    tag_assign_action = explorer.Action(
        generate_random_string(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Service Level", "Gold")}
    )
    policy_for_testing.assign_actions_to_event("VM Power On", [tag_assign_action])

    def finalize():
        policy_for_testing.assign_events()
        tag_assign_action.delete()
    request.addfinalizer(finalize)

    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)
    try:
        wait_for(
            lambda: any(
                [tag.category == "service_level" and tag.tag_name == "gold" for tag in vm.tags]
            ),
            num_sec=80,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not assigned!")


def test_action_untag(request, policy_for_testing, vm, vm_off, vm_start_func, vm_is_on_func):
    tag_unassign_action = explorer.Action(
        generate_random_string(),
        action_type="Remove Tags",
        action_values={"service_level": True}
    )
    policy_for_testing.assign_actions_to_event("VM Power On", [tag_unassign_action])

    def finalize():
        policy_for_testing.assign_events()
        tag_unassign_action.delete()
    request.addfinalizer(finalize)

    vm_start_func()
    wait_for(vm_is_on_func, num_sec=90, delay=5)
    try:
        wait_for(
            lambda: not any(
                [tag.category == "service_level" and tag.tag_name == "gold" for tag in vm.tags]
            ),
            num_sec=80,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not unassigned!")
