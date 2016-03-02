# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.control.explorer import PolicyProfile, VMCompliancePolicy, Action, VMControlPolicy
from cfme.infrastructure.virtual_machines import Vm
from utils.log import logger
from utils.providers import setup_a_provider as _setup_a_provider
from utils.wait import wait_for


@pytest.fixture(scope="module")
def setup_a_provider():
    return _setup_a_provider("infra")


@pytest.fixture(scope="module")
def vmware_provider():
    return _setup_a_provider("infra", "virtualcenter")


@pytest.fixture(scope="module")
def vmware_vm(request, vmware_provider):
    vm = VM.factory("test_control_{}".format(fauxfactory.gen_alpha().lower()), vmware_provider)
    vm.create_on_provider(find_in_cfme=True)
    request.addfinalizer(vm.delete_from_provider)
    return vm


@pytest.mark.meta(blockers=[1155284])
def test_scope_windows_registry_stuck(request, setup_a_provider):
    """If you provide Scope checking windows registry, it messes CFME up. Recoverable."""
    policy = VMCompliancePolicy(
        "Windows registry scope glitch testing Compliance Policy",
        active=True,
        scope=r"fill_registry(HKLM\SOFTWARE\Microsoft\CurrentVersion\Uninstall\test, "
        r"some value, INCLUDES, some content)"
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    policy.create()
    profile = PolicyProfile(
        "Windows registry scope glitch testing Compliance Policy",
        policies=[policy]
    )
    request.addfinalizer(lambda: profile.delete() if profile.exists else None)
    profile.create()
    # Now assign this malformed profile to a VM
    vm = VM.factory(Vm.get_first_vm_title(provider=setup_a_provider), setup_a_provider)
    vm.assign_policy_profiles(profile.description)
    # It should be screwed here, but do additional check
    pytest.sel.force_navigate("dashboard")
    pytest.sel.force_navigate("infrastructure_virtual_machines")
    assert "except" not in pytest.sel.title().lower()
    vm.unassign_policy_profiles(profile.description)


@pytest.mark.meta(blockers=[1209538], automates=[1209538])
def test_folder_field_scope(request, vmware_provider, vmware_vm):
    """This test tests the bug that makes the folder filter in expression not work.

    Prerequisities:
        * A VMware provider.
        * A VM on the provider.
        * A tag to assign.

    Steps:
        * Read the VM's 'Parent Folder Path (VMs & Templates)' from its summary page.
        * Create an action for assigning the tag to the VM.
        * Create a policy, for scope use ``Field``, field name
            ``VM and Instance : Parent Folder Path (VMs & Templates)``, ``INCLUDES`` and the
            folder name as stated on the VM's summary page.
        * Assign the ``VM Discovery`` event to the policy.
        * Assign the action to the ``VM Discovery`` event.
        * Create a policy profile and assign the policy to it.
        * Assign the policy profile to the provider.
        * Delete the VM from the CFME database.
        * Initiate provider refresh and wait for VM to appear again.
        * Assert that the VM gets tagged by the tag.
    """
    # Retrieve folder location
    folder = None
    tags = vmware_vm.get_tags()
    for tag in tags:
        if "Parent Folder Path (VMs & Templates)" in tag:
            folder = tag.split(":", 1)[-1].strip()
            logger.info("Detected folder: {}".format(folder))
            break
    else:
        pytest.fail("Could not read the folder from the tags:\n{}".format(repr(tags)))

    # Create Control stuff
    action = Action(
        fauxfactory.gen_alpha(),
        "Tag", dict(tag=("My Company Tags", "Service Level", "Platinum")))
    action.create()
    request.addfinalizer(action.delete)
    policy = VMControlPolicy(
        fauxfactory.gen_alpha(),
        scope=(
            "fill_field(VM and Instance : Parent Folder Path (VMs & Templates), "
            "INCLUDES, {})".format(folder)))
    policy.create()
    request.addfinalizer(policy.delete)
    policy.assign_events("VM Discovery")
    request.addfinalizer(policy.assign_events)  # Unassigns
    policy.assign_actions_to_event("VM Discovery", action)
    profile = PolicyProfile(fauxfactory.gen_alpha(), policies=[policy])
    profile.create()
    request.addfinalizer(profile.delete)

    # Assign policy profile to the provider
    vmware_provider.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: vmware_provider.unassign_policy_profiles(profile.description))

    # Delete and rediscover the VM
    vmware_vm.delete()
    vmware_vm.wait_for_delete()
    vmware_provider.refresh_provider_relationships()
    vmware_vm.wait_to_appear()

    # Wait for the tag to appear
    wait_for(
        vmware_vm.get_tags, num_sec=600, delay=15,
        fail_condition=lambda tags: "Service Level: Platinum" not in tags, message="vm be tagged")


@pytest.mark.meta(blockers=[1243357], automates=[1243357])
def test_invoke_custom_automation(request):
    """This test tests a bug that caused the ``Invoke Custom Automation`` fields to disappear.

    Steps:
        * Go create new action, select Invoke Custom Automation
        * The form with additional fields should appear
    """
    # The action is to have all possible fields filled, that way we can ensure it is good
    action = Action(
        fauxfactory.gen_alpha(),
        "Invoke a Custom Automation",
        dict(
            message=fauxfactory.gen_alpha(),
            request=fauxfactory.gen_alpha(),
            attribute_1=fauxfactory.gen_alpha(),
            value_1=fauxfactory.gen_alpha(),
            attribute_2=fauxfactory.gen_alpha(),
            value_2=fauxfactory.gen_alpha(),
            attribute_3=fauxfactory.gen_alpha(),
            value_3=fauxfactory.gen_alpha(),
            attribute_4=fauxfactory.gen_alpha(),
            value_4=fauxfactory.gen_alpha(),
            attribute_5=fauxfactory.gen_alpha(),
            value_5=fauxfactory.gen_alpha(),))

    @request.addfinalizer
    def _delete_action():
        if action.exists:
            action.delete()

    action.create()
