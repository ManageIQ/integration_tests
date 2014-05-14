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
from functools import wraps
from ovirtsdk.infrastructure.errors import RequestError
from utils import mgmt_system
from utils.db import cfmedb
from utils.conf import cfme_data, credentials
from utils.log import logger
from utils.miq_soap import MiqVM
from utils.providers import list_infra_providers
from utils.randomness import generate_random_string
from utils.wait import wait_for, TimedOutError

pytestmark = [pytest.mark.usefixtures("setup_infrastructure_providers")]

skipped_providers = set([])     # Holds a list of providers that were skipped so they can be skipped
                                # on next pass - py.test workaround, module-scoped fixture skipping
                                # makes skip only the current test


@pytest.fixture(scope="module", params=list_infra_providers())
def provider_id(request):
    """ This fixture ensures parametrization across multiple providers. Infra so far."""
    return request.param


@pytest.fixture(scope="module")
def provider_object(provider_id):
    """cfme/infrastructure/provider.py provider object."""
    return provider.get_from_config(provider_id)


@pytest.fixture(scope="module")
def provider_data(provider_id):
    return cfme_data["management_systems"][provider_id]


@pytest.fixture(scope="module")
def provider_credentials(provider_data):
    return credentials[provider_data["credentials"]]


@pytest.fixture(scope="module")
def vm_provider(provider_data, provider_credentials):
    """Provider object from mgmt_system.py"""
    if provider_data["type"] == "virtualcenter":
        return mgmt_system.VMWareSystem(
            provider_data["hostname"],
            provider_credentials["username"],
            provider_credentials["password"]
        )
    elif provider_data["type"] == "rhevm":
        return mgmt_system.RHEVMSystem(
            provider_data["hostname"],
            provider_credentials["username"],
            provider_credentials["password"]
        )
    # When the time comes to put the cloud stuff in
    # elif provider_data["type"] == "ec2":
    #     return mgmt_system.EC2System(
    #         username=provider_credentials["username"],
    #         password=provider_credentials["password"],
    #         region=provider_data["region"]
    #     )
    # elif provider_data["type"] == "openstack":
    #     return mgmt_system.OpenstackSystem(
    #         tenant=provider_credentials["tenant"],
    #         username=provider_credentials["username"],
    #         password=provider_credentials["password"],
    #         auth_url=provider_data["auth_url"],
    #     )
    else:
        Exception("Unknown provider!")


@pytest.fixture(scope="module")
def provider_template(provider_data):
    return (
        provider_data.get("small_template")
        or provider_data.get("provisioning", {}).get("template")
        or pytest.skip("No template!")
    )


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


@pytest.fixture(scope="module")
def vm_provisioned(vm_name, vm_provider, provider_template, provider_id, provider_data):
    if provider_id in skipped_providers:
        pytest.skip("Skipping %s" % provider_id)
    if isinstance(vm_provider, mgmt_system.RHEVMSystem):
        # RHEV-M is sometimes overloaded, so a little protection here
        try:
            vm_provider.deploy_template(
                provider_template,
                vm_name=vm_name,
                cluster_name=provider_data["default_cluster"]
            )
        except TimedOutError:
            try:
                vm_provider.delete_vm(vm_name)
            except TimedOutError:
                pass
            finally:
                # If this happened, we should skip all tests from this provider in this module
                skipped_providers.add(provider_id)
                pytest.skip("RHEV-M %s is probably full! Check its status!" % provider_id)
    elif isinstance(vm_provider, mgmt_system.VMWareSystem):
        # VMWare behaves correctly... usually, but we have to be sure! :)
        try:
            vm_provider.deploy_template(
                provider_template,
                vm_name=vm_name,
            )
        except TimedOutError:
            try:
                vm_provider.delete_vm()
            except TimedOutError:
                pass
            finally:
                # If this happened, we should skip all tests from this provider in this module
                skipped_providers.add(provider_id)
                pytest.skip("vSphere %s is probably overloaded! Check its status!" % provider_id)
    elif isinstance(vm_provider, mgmt_system.EC2System):
        pytest.skip()
    elif isinstance(vm_provider, mgmt_system.OpenstackSystem):
        pytest.skip()
    else:
        raise Exception("Unknown provider")


def get_vm_object(vm_name):
    """Looks up the CFME database for the VM.

    Args:
        vm_name: VM name
    Returns:
        If found, :py:class:`utils.miq_soap.MiqVM`. If not, `None`
    """
    vm_table = cfmedb['vms']
    for vm in cfmedb.session.query(vm_table.name, vm_table.guid)\
            .filter(vm_table.template == False):  # NOQA
        # Previous line is ok, if you change it to `is`, it won't work!
        if vm.name == vm_name:
            return MiqVM(vm.guid)
    else:
        return None


@pytest.yield_fixture(scope="module")
def vm(vm_provisioned, automate_role_set, vm_name, vm_provider, provider_object):
    """This fixture ensures that the provisioned VM appears in VMDB and returns SOAP object
    to operate on. Also ensures that the VM gets deleted after the test.
    """
    vm_obj = get_vm_object(vm_name)
    if vm_obj is None:
        provider_object.refresh_provider_relationships()
        vm_obj = wait_for(
            lambda: get_vm_object(vm_name),
            message="VM object %s appears in CFME" % vm_name,
            fail_condition=None,
            num_sec=180,
            delay=4,
        )[0]
    yield vm_obj
    logger.info("Shutting down VM with name %s" % vm_name)
    if vm_provider.is_vm_suspended(vm_name):
        logger.info("Powering up VM %s to shut it down correctly." % vm_name)
        vm_provider.start_vm(vm_name)
        wait_for(
            lambda: vm_provider.is_vm_running(vm_name),
            num_sec=240, delay=5, message="VM %s running" % vm_name
        )
    if vm_provider.is_vm_running(vm_name):
        logger.info("Powering off VM %s" % vm_name)
        vm_provider.stop_vm(vm_name)
        wait_for(
            lambda: vm_provider.is_vm_stopped(vm_name),
            num_sec=240, delay=5, message="VM %s stopped" % vm_name
        )
    logger.info("Deleting VM %s in VMDB." % vm_name)
    #vm_obj.delete()  # CFME delete
    logger.info("VM %s deleted in VMDB, now it's time to check the provider" % vm_name)
    if vm_provider.does_vm_exist(vm_name):
        logger.info("Deleting VM %s in %s" % (vm_name, vm_provider.__class__.__name__))
        vm_provider.delete_vm(vm_name)
        wait_for(
            lambda: not vm_provider.does_vm_exist(vm_name),
            num_sec=120, message="check the VM %s does not exist any more" % vm_name, delay=5
        )


def protected_from_ovirt_errors(f, name=None):
    """Try to circumvent errors by wait_for when 'Bad Request' or something similar happens."""
    class _was_req_err(object):
        pass
    if name:
        f.__name__ = name

    @wraps(f)
    def g():
        try:
            return f()
        except RequestError:
            return _was_req_err
    try:
        @wraps(g)
        def h():
            return wait_for(
                g, fail_condition=_was_req_err, num_sec=10, delay=0.25, message=g.__name__
            )[0]
        return h
    except TimedOutError:
        return False


# "PARTIAL" functions provided as fixtures. They always correspond to current `vm` object
@pytest.fixture(scope="module")
def vm_start_func(vm, vm_name, vm_provider):
    return protected_from_ovirt_errors(
        lambda: vm_provider.start_vm(vm_name), "vm_start_func-%s" % vm_name
    )


@pytest.fixture(scope="module")
def vm_stop_func(vm, vm_name, vm_provider):
    return protected_from_ovirt_errors(
        lambda: vm_provider.stop_vm(vm_name), "vm_stop_func-%s" % vm_name
    )


@pytest.fixture(scope="module")
def vm_is_on_func(vm, vm_name, vm_provider):
    return protected_from_ovirt_errors(
        lambda: vm_provider.is_vm_running(vm_name), "vm_is_on_func-%s" % vm_name
    )


@pytest.fixture(scope="module")
def vm_is_off_func(vm, vm_name, vm_provider):
    return protected_from_ovirt_errors(
        lambda: vm_provider.is_vm_stopped(vm_name), "vm_is_off_func-%s" % vm_name
    )


@pytest.fixture(scope="module")
def vm_is_suspended_func(vm, vm_name, vm_provider):
    return protected_from_ovirt_errors(
        lambda: vm_provider.is_vm_suspended(vm_name), "vm_is_suspended_func-%s" % vm_name
    )


@pytest.fixture(scope="module")
def vm_in_steady_state_func(vm_is_off_func, vm_is_on_func, vm_is_suspended_func):
    """To prevent errors from launching a machine which is currently suspending and so,
    one can use this fixture for wait_for to guarantee that the VM is in steady state.
    """
    return protected_from_ovirt_errors(
        lambda: vm_is_off_func() or vm_is_on_func() or vm_is_suspended_func(),
        "vm_in_steady_state_func"
    )


@pytest.fixture(scope="function")
def vm_on(vm_start_func, vm_is_on_func, vm_in_steady_state_func, vm_name, vm_provider):
    """ Ensures that the VM is on when the control goes to the test."""
    wait_for(vm_in_steady_state_func, message="wait for VM %s to settle" % vm_name, delay=1)
    if not vm_is_on_func():
        logger.info("Powering on %s in provider %s" % (vm_name, vm_provider.__class__.__name__))
        vm_start_func()
        wait_for(vm_is_on_func, num_sec=240, delay=5, message="Wait %s on" % vm_name)


@pytest.fixture(scope="function")
def vm_off(
        vm_stop_func, vm_is_off_func, vm_is_suspended_func, vm_start_func, vm_is_on_func, vm_name,
        vm_provider, vm_in_steady_state_func):
    """ Ensures that the VM is off when the control goes to the test."""
    wait_for(vm_in_steady_state_func, message="wait for VM %s to settle" % vm_name, delay=1)
    if not vm_is_off_func():
        if vm_is_suspended_func():
            logger.info("Powering on %s from suspend to power off without exception" % vm_name)
            vm_start_func()
            wait_for(vm_is_on_func, num_sec=240, delay=5, message="Wait %s on for pwroff" % vm_name)
        logger.info("Powering off %s in provider %s" % (vm_name, vm_provider.__class__.__name__))
        vm_stop_func()
        wait_for(vm_is_off_func, num_sec=240, delay=5, message="Wait %s off" % vm_name)


@pytest.yield_fixture(scope="module")
def policy_for_testing(vm_provisioned, policy_name, policy_profile_name, provider_object, vm_name):
    """ Takes care of setting the appliance up for testing """
    policy = explorer.VMControlPolicy(
        policy_name,
        scope="fill_field(VM and Instance : Name, INCLUDES, %s)" % vm_name
    )
    policy.create()
    policy_profile = explorer.PolicyProfile(policy_profile_name, policies=[policy])
    policy_profile.create()
    provider_object.assign_policy_profiles(policy_profile_name)
    yield policy
    provider_object.unassign_policy_profiles(policy_profile_name)
    policy_profile.delete()
    policy.delete()


def test_action_start_virtual_machine_after_stopping(
        request, policy_for_testing, vm_name, vm_on, vm_stop_func, vm_is_off_func, vm_is_on_func):
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
        wait_for(vm_is_off_func, num_sec=80, delay=5)
    except TimedOutError:
        pass
    # Wait for VM powered on by CFME
    try:
        wait_for(vm_is_on_func, num_sec=240, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power on the VM %s" % vm_name)


def test_action_stop_virtual_machine_after_starting(
        request, policy_for_testing, vm_name, vm_off, vm_start_func, vm_is_on_func, vm_is_off_func):
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
        wait_for(vm_is_on_func, num_sec=80, delay=5)
    except TimedOutError:
        pass
    # Wait for VM powered off by CFME
    try:
        wait_for(vm_is_off_func, num_sec=240, delay=5)
    except TimedOutError:
        pytest.fail("CFME did not power off the VM %s" % vm_name)


def test_action_suspend_virtual_machine_after_starting(
        request, policy_for_testing, vm_off, vm_name, vm_start_func, vm_is_on_func,
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
        wait_for(vm_is_suspended_func, num_sec=300, delay=5)
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
        wait_for(vm_is_on_func, num_sec=300, delay=5)
    except TimedOutError:
        pass  # VM did not start, so that's what we want
    else:
        pytest.fail("CFME did not prevent starting of the VM %s" % vm_name)


def test_action_power_on_logged(
        request, policy_for_testing, vm_off, ssh_client, vm_name, vm_start_func, vm_is_on_func):
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
        if rc != 0:  # Nothing found, so shortcut
            return False
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
    wait_for(search_logs, num_sec=180, message="log search")


def test_action_power_on_audit(
        request, policy_for_testing, vm_off, ssh_client, vm_start_func, vm_is_on_func):
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
        if rc != 0:  # Nothing found, so shortcut
            return False
        for line in stdout.strip().split("\n"):
            if not "Policy success" in line or "MiqAction.action_audit" not in line:
                continue
            match_string = "policy: [%s], event: [VM Power On]" % (policy_desc)
            if match_string in line:
                logger.info("Found corresponding log message: %s" % line.strip())
                return True
        else:
            return False
    wait_for(search_logs, num_sec=180, message="log search")


def test_action_create_snapshot_and_delete_last(
        request, policy_for_testing, vm, vm_on, vm_stop_func, vm_is_off_func, vm_start_func,
        vm_is_on_func, vm_provider):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete Most Recent Snapshot'.

    This test sets the policy that it makes snapshot of VM after it's powered off and when it is
    powered back on, it deletes the last snapshot.
    """
    if isinstance(vm_provider, mgmt_system.RHEVMSystem):
        pytest.skip("No snapshots on RHEV")
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
        vm_is_off_func, vm_provider):
    """ This test tests actions 'Create a Snapshot' (custom) and 'Delete all Snapshots'.

    This test sets the policy that it makes snapshot of VM after it's powered off and then it cycles
    several time that it generates a couple of snapshots. Then the 'Delete all Snapshots' is
    assigned to power on event, VM is powered on and it waits for all snapshots to disappear.
    """
    if isinstance(vm_provider, mgmt_system.RHEVMSystem):
        pytest.skip("No snapshots on RHEV")
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
        request, policy_for_testing, vm, vm_on, ssh_client, vm_stop_func, vm_is_off_func):
    """ This test tests actions 'Raise Automation Event'.

    This test sets the policy that it raises an automation event VM after it's powered on.
    Then it checks logs whether that really happened.
    """
    # Set up the policy and prepare finalizer
    policy_for_testing.assign_actions_to_event("VM Power Off", ["Raise Automation Event"])
    request.addfinalizer(lambda: policy_for_testing.assign_events())
    # Start the VM
    vm_stop_func()
    wait_for(vm_is_off_func, num_sec=90, delay=5)

    # Search the logs
    def search_logs():
        rc, stdout = ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/automation.log | grep 'MiqAeEvent.build_evm_event' |"
            " grep 'event=<\"vm_poweroff\">' | grep 'id: %s'" % vm.object.id
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
    wait_for(vm_is_on_func, num_sec=120, delay=5)
    try:
        wait_for(
            lambda: any(
                [tag.category == "service_level" and tag.tag_name == "gold" for tag in vm.tags]
            ),
            num_sec=600,
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
    wait_for(vm_is_on_func, num_sec=120, delay=5)
    try:
        wait_for(
            lambda: not any(
                [tag.category == "service_level" and tag.tag_name == "gold" for tag in vm.tags]
            ),
            num_sec=600,
            message="tag presence check"
        )
    except TimedOutError:
        pytest.fail("Tags were not unassigned!")
