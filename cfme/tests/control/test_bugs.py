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
def vmware_vm(request, virtualcenter_provider):
    vm = VM.factory(random_vm_name("control"), virtualcenter_provider)
    vm.create_on_provider(find_in_cfme=True)
    request.addfinalizer(vm.delete_from_provider)
    return vm


@pytest.mark.meta(blockers=[1155284])
def test_scope_windows_registry_stuck(request, infra_provider):
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
    vm = VM.factory(Vm.get_first_vm_title(provider=infra_provider), infra_provider)
    vm.assign_policy_profiles(profile.description)
    # It should be screwed here, but do additional check
    navigate_to(Server, 'Dashboard')
    navigate_to(Vm, 'All')
    assert "except" not in pytest.sel.title().lower()
    vm.unassign_policy_profiles(profile.description)


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
def test_check_compliance_history(request, virtualcenter_provider, vmware_vm):
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
    virtualcenter_provider.assign_policy_profiles(policy_profile.description)
    request.addfinalizer(lambda: virtualcenter_provider.unassign_policy_profiles(
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
