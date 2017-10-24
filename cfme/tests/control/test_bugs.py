# -*- coding: utf-8 -*-
from collections import namedtuple
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base import Server
from cfme.common.vm import VM
from cfme.exceptions import CFMEExceptionOccured
from cfme.control.explorer.policies import VMCompliancePolicy, VMControlPolicy
from cfme.control.explorer.alerts import AlertDetailsView
from cfme.control.explorer.conditions import VMCondition
from cfme.infrastructure.virtual_machines import Vm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.appliance import get_or_create_current_appliance
from cfme.utils.blockers import BZ
from widgetastic.widget import Text


pytestmark = [
    test_requirements.control,
    pytest.mark.tier(3)
]


@pytest.fixture(scope="module")
def policy_profile_collection(appliance):
    return appliance.collections.policy_profiles


@pytest.fixture(scope="module")
def policy_collection(appliance):
    return appliance.collections.policies


@pytest.fixture(scope="module")
def condition_collection(appliance):
    return appliance.collections.conditions


@pytest.fixture(scope="module")
def action_collection(appliance):
    return appliance.collections.actions


@pytest.fixture(scope="module")
def alert_collection(appliance):
    return appliance.collections.alerts


def create_policy(request, collection):
    args = (VMControlPolicy, fauxfactory.gen_alpha())
    kwargs = {}
    policy = collection.create(*args)

    @request.addfinalizer
    def _delete():
        while policy.exists:
            policy.delete()

    return args, kwargs


def create_condition(request, collection):
    args = (
        VMCondition,
        fauxfactory.gen_alpha(),
        "fill_field(VM and Instance : Boot Time, BEFORE, Today)"
    )
    kwargs = {}
    condition = collection.create(*args)

    @request.addfinalizer
    def _delete():
        while condition.exists:
            condition.delete()

    return args, kwargs


def create_action(request, collection):
    args = (fauxfactory.gen_alpha(),)
    kwargs = {
        "action_type": "Tag",
        "action_values": {"tag": ("My Company Tags", "Department", "Accounting")}
    }
    action = collection.create(*args, **kwargs)

    @request.addfinalizer
    def _delete():
        while action.exists:
            action.delete()

    return args, kwargs


def create_alert(request, collection):
    args = (fauxfactory.gen_alpha(),)
    kwargs = {"timeline_event": True, "driving_event": "Hourly Timer"}
    alert = collection.create(*args, **kwargs)

    @request.addfinalizer
    def _delete():
        while alert.exists:
            alert.delete()

    return args, kwargs


ProfileCreateFunction = namedtuple('ProfileCreateFunction', ['name', 'fn'])

items = [
    ProfileCreateFunction("Policies", create_policy),
    ProfileCreateFunction("Conditions", create_condition),
    ProfileCreateFunction("Actions", create_action),
    ProfileCreateFunction("Alerts", create_alert)
]


@pytest.fixture(scope="module")
def collections(policy_collection, condition_collection, action_collection, alert_collection):
    return {
        "Policies": policy_collection,
        "Conditions": condition_collection,
        "Actions": action_collection,
        "Alerts": alert_collection
    }


@pytest.fixture
def vmware_vm(request, virtualcenter_provider):
    vm = VM.factory(random_vm_name("control"), virtualcenter_provider)
    vm.create_on_provider(find_in_cfme=True)
    request.addfinalizer(vm.delete_from_provider)
    return vm


@pytest.yield_fixture
def hardware_reconfigured_alert(alert_collection):
    alert = alert_collection.create(
        fauxfactory.gen_alpha(),
        evaluate=("Hardware Reconfigured", {"hardware_attribute": "RAM"}),
        timeline_event=True
    )
    yield alert
    alert.delete()


@pytest.mark.meta(blockers=[1155284])
def test_scope_windows_registry_stuck(request, infra_provider, policy_collection,
        policy_profile_collection):
    """If you provide Scope checking windows registry, it messes CFME up. Recoverable."""
    policy = policy_collection.create(
        VMCompliancePolicy,
        "Windows registry scope glitch testing Compliance Policy",
        active=True,
        scope=r"fill_registry(HKLM\SOFTWARE\Microsoft\CurrentVersion\Uninstall\test, "
        r"some value, INCLUDES, some content)"
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    profile = policy_profile_collection.create(
        "Windows registry scope glitch testing Compliance Policy",
        policies=[policy]
    )
    request.addfinalizer(lambda: profile.delete() if profile.exists else None)
    # Now assign this malformed profile to a VM
    vm = VM.factory(Vm.get_first_vm(provider=infra_provider).name, infra_provider)
    vm.assign_policy_profiles(profile.description)
    # It should be screwed here, but do additional check
    navigate_to(Server, 'Dashboard')
    navigate_to(Vm, 'All')
    assert "except" not in pytest.sel.title().lower()
    vm.unassign_policy_profiles(profile.description)


@pytest.mark.meta(blockers=[1243357], automates=[1243357])
def test_invoke_custom_automation(request, action_collection):
    """This test tests a bug that caused the ``Invoke Custom Automation`` fields to disappear.

    Steps:
        * Go create new action, select Invoke Custom Automation
        * The form with additional fields should appear
    """
    # The action is to have all possible fields filled, that way we can ensure it is good
    action = action_collection.create(
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
            value_5=fauxfactory.gen_alpha()
        )
    )
    request.addfinalizer(lambda: action.delete() if action.exists else None)


@pytest.mark.meta(blockers=[1375093], automates=[1375093])
def test_check_compliance_history(request, virtualcenter_provider, vmware_vm, policy_collection,
        policy_profile_collection):
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
    policy = policy_collection.create(
        VMCompliancePolicy,
        "Check compliance history policy {}".format(fauxfactory.gen_alpha()),
        active=True,
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vmware_vm.name)
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    policy_profile = policy_profile_collection.create(policy.description, policies=[policy])
    request.addfinalizer(lambda: policy_profile.delete() if policy_profile.exists else None)
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


@pytest.mark.meta(blockers=[BZ(1395965, forced_streams=["5.6", "5.7"]),
                            BZ(1491576, forced_streams=["5.7"])])
def test_delete_all_actions_from_compliance_policy(request, policy_collection):
    """We should not allow a compliance policy to be saved
    if there are no actions on the compliance event.

    Steps:
        * Create a compliance policy
        * Remove all actions

    Result:
        The policy shouldn't be saved.
    """
    policy = policy_collection.create(VMCompliancePolicy, fauxfactory.gen_alphanumeric())
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    with pytest.raises(AssertionError):
        policy.assign_actions_to_event("VM Compliance Check", [])


@pytest.mark.parametrize("create_function", items, ids=[item.name for item in items])
def test_control_identical_descriptions(request, create_function, collections):
    """CFME should not allow to create policy, alerts, profiles, actions and others to be created
    if the item with the same description already exists.

    Steps:
        * Create an item
        * Create the same item again

    Result:
        The item shouldn't be created.
    """
    args, kwargs = create_function.fn(request, collections[create_function.name])
    with pytest.raises(AssertionError):
        collections[create_function.name].create(*args, **kwargs)


@pytest.mark.meta(blockers=[1231889], automates=[1231889])
def test_vmware_alarm_selection_does_not_fail(alert_collection):
    """Test the bug that causes CFME UI to explode when VMware Alarm type is selected.

    Metadata:
        test_flag: alerts
    """
    alert_obj = alert_collection.instantiate(
        "Trigger by CPU {}".format(fauxfactory.gen_alpha(length=4)),
        active=True,
        based_on="VM and Instance",
        evaluate=("VMware Alarm", {}),
        notification_frequency="5 Minutes"
    )
    try:
        alert_collection.create(
            "Trigger by CPU {}".format(fauxfactory.gen_alpha(length=4)),
            active=True,
            based_on="VM and Instance",
            evaluate=("VMware Alarm", {}),
            notification_frequency="5 Minutes"
        )
    except CFMEExceptionOccured as e:
        pytest.fail("The CFME has thrown an error: {}".format(str(e)))
    except Exception as e:
        view = alert_obj.create_view(AlertDetailsView)
        view.flash.assert_message("At least one of E-mail, SNMP Trap, Timeline Event, or"
            " Management Event must be configured")
    else:
        pytest.fail("Creating this alert passed although it must fail.")


def test_alert_ram_reconfigured(hardware_reconfigured_alert):
    """Tests the bug when it was not possible to save an alert with RAM option in hardware
    attributes.
    """
    view = navigate_to(hardware_reconfigured_alert, "Details")
    attr = view.hardware_reconfigured_parameters.get_text_of("Hardware Attribute")
    assert attr == "RAM Increased"
