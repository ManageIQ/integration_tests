# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.base import Server
from cfme.common.vm import VM
from cfme.control.explorer.policy_profiles import PolicyProfile
from cfme.control.explorer.policies import VMCompliancePolicy, VMControlPolicy
from cfme.control.explorer.actions import Action
from cfme.control.explorer.alerts import Alert
from cfme.control.explorer.conditions import VMCondition
from cfme.control.explorer.alert_profiles import VMInstanceAlertProfile
from cfme.infrastructure.virtual_machines import Vm
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from utils.log import logger
from utils.providers import setup_a_provider as _setup_a_provider
from utils.wait import wait_for
from cfme import test_requirements
from utils.generators import random_vm_name
from widgetastic.widget import Text
from utils.appliance import get_or_create_current_appliance
from utils.blockers import BZ


pytestmark = [
    test_requirements.control,
    pytest.mark.tier(3)
]


def create_policy_profile(request):
    random_string = fauxfactory.gen_alpha()
    policy = VMControlPolicy(random_string)
    policy.create()
    policy_profile = PolicyProfile(random_string, [policy])
    policy_profile.create()

    @request.addfinalizer
    def _delete():
        while policy_profile.exists:
            policy_profile.delete()
        if policy.exists:
            policy.delete()

    return policy_profile


def create_policy(request):
    policy = VMControlPolicy(fauxfactory.gen_alpha())
    policy.create()

    @request.addfinalizer
    def _delete():
        while policy.exists:
            policy.delete()

    return policy


def create_condition(request):
    condition = VMCondition(
        fauxfactory.gen_alpha(),
        "fill_field(VM and Instance : Boot Time, BEFORE, Today)"
    )
    condition.create()

    @request.addfinalizer
    def _delete():
        while condition.exists:
            condition.delete()

    return condition


def create_action(request):
    action = Action(
        fauxfactory.gen_alpha(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )
    action.create()

    @request.addfinalizer
    def _delete():
        while action.exists:
            action.delete()

    return action


def create_alert_profile(request):
    alert = Alert("VM CD Drive or Floppy Connected")
    alert_profile = VMInstanceAlertProfile(fauxfactory.gen_alpha(), [alert])
    alert_profile.create()

    @request.addfinalizer
    def _delete():
        while alert_profile.exists:
            alert_profile.delete()

    return alert_profile


def create_alert(request):
    random_string = fauxfactory.gen_alpha()
    alert = Alert(
        random_string, timeline_event=True, driving_event="Hourly Timer"
    )
    alert.create()

    @request.addfinalizer
    def _delete():
        while alert.exists:
            alert.delete()

    return alert


items = [
    ("Policy profiles", create_policy_profile),
    ("Policies", create_policy),
    ("Conditions", create_condition),
    ("Actions", create_action),
    ("Alert profiles", create_alert_profile),
    ("Alerts", create_alert)
]


@pytest.fixture(scope="module")
def setup_a_provider():
    return _setup_a_provider("infra")


@pytest.fixture(scope="module")
def vmware_provider():
    return _setup_a_provider("infra", "virtualcenter")


@pytest.fixture(scope="module")
def vmware_vm(request, vmware_provider):
    vm = VM.factory(random_vm_name("control"), vmware_provider)
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
    navigate_to(Server, 'Dashboard')
    navigate_to(Vm, 'All')
    assert "except" not in pytest.sel.title().lower()
    vm.unassign_policy_profiles(profile.description)


@pytest.mark.meta(blockers=[1209538], automates=[1209538])
@pytest.mark.skipif(current_version() > "5.5", reason="requires cfme 5.5 and lower")
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
    if any(tag.category.display_name == "Parent Folder Path (VMs & Templates)" for tag in tags):
        folder = ', '.join(
            item.display_name for item in
            [tag for tag in tags
             if tag.category.display_name == "Parent Folder Path (VMs & Templates)"])
        logger.info("Detected folder: %s", folder)
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
        fail_condition=lambda tags: not any(
            tag.category.display_name == "Service Level" and tag.display_name == "Platinum"
            for tag in tags),
        message="vm be tagged")


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


@pytest.mark.meta(blockers=[1375093], automates=[1375093])
def test_check_compliance_history(request, vmware_provider, vmware_vm):
    """This test checks if compliance history link in a VM details screen work.

    Steps:
        * Create any VM compliance policy
        * Assign it to a policy profile
        * Assign the policy profile to any VM
        * Perform the compliance check for the VM
        * Go to the VM details screen
        * Click on "History" row in Compliance InfoBox

    Result:
        Compliance history screen with last 10 checks should be opened
    """
    policy = VMCompliancePolicy(
        "Check compliance history policy {}".format(fauxfactory.gen_alpha()),
        active=True,
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vmware_vm.name)
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    policy.create()
    policy_profile = PolicyProfile(
        policy.description,
        policies=[policy]
    )
    request.addfinalizer(lambda: policy_profile.delete() if policy_profile.exists else None)
    policy_profile.create()
    vmware_provider.assign_policy_profiles(policy_profile.description)
    request.addfinalizer(lambda: vmware_provider.unassign_policy_profiles(
        policy_profile.description))
    vmware_vm.check_compliance()
    vmware_vm.open_details(["Compliance", "History"])
    appliance = get_or_create_current_appliance()
    history_screen_title = Text(appliance.browser.widgetastic,
        "//span[@id='explorer_title_text']").text
    assert history_screen_title == '"Compliance History" for Virtual Machine "{}"'.format(
        vmware_vm.name)


@pytest.mark.meta(blockers=[BZ(1395965, forced_streams=["5.6", "5.7"])])
def test_delete_all_actions_from_compliance_policy(request):
    """We should not allow a compliance policy to be saved
    if there are no actions on the compliance event.

    Steps:
        * Create a compliance policy
        * Remove all actions

    Result:
        The policy shouldn't be saved.
    """
    policy = VMCompliancePolicy(fauxfactory.gen_alphanumeric())

    @request.addfinalizer
    def _delete_policy():
        if policy.exists:
            policy.delete()

    policy.create()
    with pytest.raises(AssertionError):
        policy.assign_actions_to_event("VM Compliance Check", [])


@pytest.mark.parametrize("item_type,create_function", items, ids=[item[0] for item in items])
@pytest.mark.uncollectif(lambda item_type: item_type in ["Policy profiles", "Alert profiles"] and
    BZ(1304396, forced_streams=["5.6", "5.7"]).blocks)
def test_control_identical_descriptions(request, item_type, create_function):
    """CFME should not allow to create policy, alerts, profiles, actions and others to be created
    if the item with the same description already exists.

    Steps:
        * Create an item
        * Create the same item again

    Result:
        The item shouldn't be created.
    """
    item = create_function(request)
    with pytest.raises(AssertionError):
        item.create()
