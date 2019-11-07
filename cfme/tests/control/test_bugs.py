# -*- coding: utf-8 -*-
import random
from collections import namedtuple
from datetime import datetime

import fauxfactory
import pytest
from widgetastic.widget import Text

from cfme import test_requirements
from cfme.control.explorer import conditions
from cfme.control.explorer import ControlExplorerView
from cfme.control.explorer.alert_profiles import ServerAlertProfile
from cfme.control.explorer.policies import VMCompliancePolicy
from cfme.control.explorer.policies import VMControlPolicy
from cfme.exceptions import CFMEExceptionOccured
from cfme.tests.control.test_basic import CONDITIONS
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.control,
    pytest.mark.tier(3)
]

BAD_CONDITIONS = [
    conditions.ReplicatorCondition,
    conditions.PodCondition,
    conditions.ContainerNodeCondition,
    conditions.ContainerImageCondition,
    conditions.ProviderCondition
]


BREADCRUMB_LOCATIONS = dict(
    ControlExplorer=["Control", "Explorer", "Policy Profiles", "All Policy Profiles"],
    ControlSimulation=["Control", "Simulation", "Policies"],
    ControlImportExport=["Control", "Import / Export"],
    ControlLog=["Control", "Log"]
)


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
        conditions.VMCondition,
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
def collections(appliance):
    return {
        "Policies": appliance.collections.policies,
        "Conditions": appliance.collections.conditions,
        "Actions": appliance.collections.actions,
        "Alerts": appliance.collections.alerts
    }


@pytest.fixture
def vmware_vm(request, virtualcenter_provider):
    vm = virtualcenter_provider.appliance.collections.infra_vms.instantiate(
        random_vm_name("control"),
        virtualcenter_provider
    )
    vm.create_on_provider(find_in_cfme=True)
    request.addfinalizer(vm.cleanup_on_provider)
    return vm


@pytest.fixture
def hardware_reconfigured_alert(appliance):
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alpha(),
        evaluate=("Hardware Reconfigured", {"hardware_attribute": "RAM"}),
        timeline_event=True
    )
    yield alert
    alert.delete()


@pytest.fixture
def setup_disk_usage_alert(appliance):
    # get the current time
    timestamp = datetime.now()
    # setup the DB query
    table = appliance.db.client['miq_alert_statuses']
    query = appliance.db.client.session.query(table.description, table.evaluated_on)
    # configure the advanced settings and place a large file on the appliance
    # disk usage above 1 % will now trigger a disk_usage event
    appliance.update_advanced_settings(
        {"server": {"events": {"disk_usage_gt_percent": 1}}}
    )
    # create a 1 GB file on /var/www/miq/vmdb/log

    result = appliance.ssh_client.run_command(
        "dd if=/dev/zero of=/var/www/miq/vmdb/log/delete_me.txt count=1024 bs=1048576"
    )
    # verify that the command was successful
    assert not result.failed
    # setup the alert for firing
    expression = {"expression": "fill_count(Server.EVM Workers, >, 0)"}
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alpha(),
        based_on='Server',
        evaluate=("Expression (Custom)", expression),
        driving_event="Appliance Operation: Server High /var/www/miq/vmdb/log Disk Usage",
        notification_frequency="1 Minute",
    )
    alert_profile = appliance.collections.alert_profiles.create(
        ServerAlertProfile,
        "Alert profile for {}".format(alert.description),
        alerts=[alert]
    )
    alert_profile.assign_to("Selected Servers", selections=["Servers", "EVM"])
    yield alert, timestamp, query
    alert_profile.delete()
    alert.delete()
    appliance.update_advanced_settings(
        {"server": {"events": {"disk_usage_gt_percent": "<<reset>>"}}}
    )
    result = appliance.ssh_client.run_command("rm /var/www/miq/vmdb/log/delete_me.txt")
    # verify that the command was successful
    assert not result.failed


@pytest.fixture
def action_for_testing(appliance):
    action_ = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )
    yield action_
    action_.delete()


@pytest.fixture
def compliance_condition(appliance, virtualcenter_provider):
    try:
        vm_name = virtualcenter_provider.data["cap_and_util"]["capandu_vm"]
    except KeyError:
        pytest.skip("Missing 'cap_and_util' field in {} provider data.".format(
            virtualcenter_provider.key)
        )
    expression = (
        "fill_field(VM and Instance : Name, =, {}); "
        "select_expression_text; "
        "click_or; "
        "fill_field(VM and Instance : Name, =, {}); "
        "select_expression_text; "
        "click_or; "
        "fill_field(VM and Instance : Name, =, {}); "
    ).format(vm_name, fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric())
    condition = appliance.collections.conditions.create(
        conditions.VMCondition,
        fauxfactory.gen_alphanumeric(12, start="vm-name-"),
        expression=expression
    )
    yield condition
    condition.delete()


@pytest.fixture
def vm_compliance_policy_profile(appliance, compliance_condition):
    policy = appliance.collections.policies.create(
        VMCompliancePolicy, fauxfactory.gen_alphanumeric(20, start="vm-compliance-")
    )
    policy.assign_conditions(compliance_condition)
    profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alphanumeric(26, start="VM Compliance Profile "),
        [policy],
    )
    yield profile
    profile.delete()
    policy.delete()


@pytest.mark.meta(blockers=[BZ(1155284)], automates=[1155284])
def test_scope_windows_registry_stuck(request, appliance, infra_provider):
    """If you provide Scope checking windows registry, it messes CFME up. Recoverable.

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: low
        initialEstimate: 1/6h

    Bugzilla:
        1155284
    """
    policy = appliance.collections.policies.create(
        VMCompliancePolicy,
        "Windows registry scope glitch testing Compliance Policy",
        active=True,
        scope=r"fill_registry(HKLM\SOFTWARE\Microsoft\CurrentVersion\Uninstall\test, "
        r"some value, INCLUDES, some content)"
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    profile = appliance.collections.policy_profiles.create(
        "Windows registry scope glitch testing Compliance Policy",
        policies=[policy]
    )
    request.addfinalizer(lambda: profile.delete() if profile.exists else None)
    # Now assign this malformed profile to a VM
    # not assuming tht infra_provider is actually an InfraProvider type
    vm = infra_provider.appliance.collections.infra_vms.all()[0]
    vm.assign_policy_profiles(profile.description)
    # It should be screwed here, but do additional check
    navigate_to(appliance.server, 'Dashboard')
    view = navigate_to(appliance.collections.infra_vms, 'All')
    assert "except" not in view.entities.title.text.lower()
    vm.unassign_policy_profiles(profile.description)


@pytest.mark.meta(blockers=[BZ(1243357)], automates=[1243357])
def test_invoke_custom_automation(request, appliance):
    """This test tests a bug that caused the ``Invoke Custom Automation`` fields to disappear.

    Steps:
        * Go create new action, select Invoke Custom Automation
        * The form with additional fields should appear

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/6h

    Bugzilla:
        1243357
    """
    # The action is to have all possible fields filled, that way we can ensure it is good
    action = appliance.collections.actions.create(
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


@pytest.mark.meta(blockers=[BZ(1375093)], automates=[1375093])
def test_check_compliance_history(request, virtualcenter_provider, vmware_vm, appliance):
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

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control

    Bugzilla:
        1375093
    """
    policy = appliance.collections.policies.create(
        VMCompliancePolicy,
        fauxfactory.gen_alpha(36, start="Check compliance history policy "),
        active=True,
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vmware_vm.name)
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    policy_profile = appliance.collections.policy_profiles.create(
        policy.description, policies=[policy]
    )
    request.addfinalizer(lambda: policy_profile.delete() if policy_profile.exists else None)
    virtualcenter_provider.assign_policy_profiles(policy_profile.description)
    request.addfinalizer(lambda: virtualcenter_provider.unassign_policy_profiles(
        policy_profile.description))
    vmware_vm.check_compliance()
    vmware_vm.open_details(["Compliance", "History"])
    history_screen_title = Text(appliance.browser.widgetastic,
        "//span[@id='explorer_title_text']").text
    assert history_screen_title == '"Compliance History" for Virtual Machine "{}"'.format(
        vmware_vm.name)


@pytest.mark.meta(blockers=[BZ(1395965), BZ(1491576)], automates=[1395965])
def test_delete_all_actions_from_compliance_policy(request, appliance):
    """We should not allow a compliance policy to be saved
    if there are no actions on the compliance event.

    Steps:
        * Create a compliance policy
        * Remove all actions

    Result:
        The policy shouldn't be saved.

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h

    Bugzilla:
        1395965
        1491576
    """
    policy = appliance.collections.policies.create(
        VMCompliancePolicy, fauxfactory.gen_alphanumeric()
    )
    request.addfinalizer(lambda: policy.delete() if policy.exists else None)
    with pytest.raises(AssertionError):
        policy.assign_actions_to_event("VM Compliance Check", [])


@pytest.mark.parametrize("create_function", items, ids=[item.name for item in items])
def test_control_identical_descriptions(request, create_function, collections, appliance):
    """CFME should not allow to create policy, alerts, profiles, actions and others to be created
    if the item with the same description already exists.

    Steps:
        * Create an item
        * Create the same item again

    Result:
        The item shouldn't be created.

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: low
        initialEstimate: 1/12h
    """
    args, kwargs = create_function.fn(request, collections[create_function.name])
    flash = appliance.browser.create_view(ControlExplorerView).flash
    try:
        collections[create_function.name].create(*args, **kwargs)
    except (TimedOutError, AssertionError):
        flash.assert_message("Description has already been taken")
        # force navigation away from the page so the browser is not stuck on the edit page
        navigate_to(appliance.server, 'ControlExplorer', force=True)


@pytest.mark.meta(blockers=[BZ(1231889)], automates=[1231889])
def test_vmware_alarm_selection_does_not_fail(request, appliance):
    """Test the bug that causes CFME UI to explode when VMware Alarm type is selected.
        We assert that the alert using this type is simply created. Then we destroy
        the alert.

    Metadata:
        test_flag: alerts

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: low
        initialEstimate: 1/12h
    """
    try:
        alert = appliance.collections.alerts.create(
            fauxfactory.gen_alpha(length=20, start="Trigger by CPU "),
            active=True,
            based_on="VM and Instance",
            evaluate=("VMware Alarm", {}),
            notification_frequency="5 Minutes"
        )
        request.addfinalizer(lambda: alert.delete() if alert.exists else None)
    except CFMEExceptionOccured as e:
        pytest.fail("CFME has thrown an error: {}".format(str(e)))


def test_alert_ram_reconfigured(hardware_reconfigured_alert):
    """Tests the bug when it was not possible to save an alert with RAM option in hardware
    attributes.

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(hardware_reconfigured_alert, "Details")
    attr = view.hardware_reconfigured_parameters.get_text_of("Hardware Attribute")
    assert attr == "RAM Increased"


@pytest.mark.tier(2)
@test_requirements.alert
@pytest.mark.meta(automates=[1658670, 1672698])
def test_alert_for_disk_usage(setup_disk_usage_alert):
    """
    Bugzilla:
        1658670
        1672698

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. Go to Control > Explorer > Alerts
            2. Configuration > Add new alert
            3. Based on = Server
            4. What to evaluate = Expression (Custom)
            5. Driving Event =
                "Appliance Operation: Server High /var/www/miq/vmdb/log Disk Usage"
            6. Assign the alert to a Alert Profile
            7. Assign the Alert Profile to the Server
            8. In advanced config, change:
                events:
                  :disk_usage_gt_percent: 80
                to:
                  events:
                  :disk_usage_gt_percent: 1
            9. dd a file in /var/www/miq/vmdb/log large enough to trigger 1% disk usage
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8.
            9. the alert should fire, and the event of type
                "evm_server_log_disk_usage" should trigger
    """
    alert, timestamp, query = setup_disk_usage_alert

    def _check_query():
        query_result = query.all()
        if query_result:
            # here query_result[0][0] and query_result[0][1] correspond to the description and
            # timestamp pulled from the database, respectively
            return alert.description == query_result[0][0] and timestamp < query_result[0][1]
        else:
            return False

    # wait for the alert to appear in the miq_alert_statuses table
    wait_for(
        _check_query,
        delay=5,
        num_sec=600,
        message="Waiting for alert {} to appear in DB".format(alert.description)
    )


@pytest.mark.parametrize(
    "condition_class", CONDITIONS, ids=lambda condition_class: condition_class.__name__
)
@pytest.mark.meta(automates=[1683697])
def test_accordion_after_condition_creation(appliance, condition_class):
    """
    Bugzilla:
        1683697

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h

    For this test, we must make a condition 'manually' and so that we can access the view
    during the condition creation.
    """
    if BZ(1683697).blocks and condition_class in BAD_CONDITIONS:
        pytest.skip("Skipping because {} conditions are impacted by BZ 1683697"
                    .format(condition_class.__name__))
    condition = appliance.collections.conditions.create(condition_class,
        fauxfactory.gen_alpha(),
        expression="fill_field({} : Name, IS NOT EMPTY)".format(
            condition_class.FIELD_VALUE)
    )
    view = condition.create_view(conditions.ConditionDetailsView, wait="10s")
    assert view.conditions.tree.currently_selected == [
        "All Conditions", "{} Conditions".format(condition_class.TREE_NODE), condition.description
    ]


@pytest.mark.meta(blockers=[BZ(1708434)], automates=[1708434])
def test_edit_action_buttons(action_for_testing):
    """
    This tests the bug where the save/reset button are always enabled, even on initial load.

    Bugzilla:
        1708434

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/30h
    """
    view = navigate_to(action_for_testing, "Edit")

    assert view.save_button.disabled
    assert view.reset_button.disabled
    # click the cancel button and navigate to "Details" so that the action can be deleted
    view.cancel_button.click()
    navigate_to(action_for_testing, "Details")


@pytest.mark.meta(blockers=[BZ(1717483)], automates=[1711352])
def test_policy_condition_multiple_ors(
        appliance,
        virtualcenter_provider,
        vm_compliance_policy_profile
):
    """
    Tests to make sure that policy conditions with multiple or statements work properly

    Bugzilla:
        1711352
        1717483

    Polarion:
        assignee: jdupuy
        caseimportance: low
        casecomponent: Control
        initialEstimate: 1/12h
    """
    collection = appliance.provider_based_collection(virtualcenter_provider)
    all_vms = collection.all()
    all_vm_names = [vm.name for vm in all_vms]

    # we need to select out cu-24x7
    vm_name = virtualcenter_provider.data["cap_and_util"]["capandu_vm"]
    # check that it exists on provider
    if not virtualcenter_provider.mgmt.does_vm_exist(vm_name):
        pytest.skip("No capandu_vm available on virtualcenter_provider of name {}".format(vm_name))

    vms = [all_vms.pop(all_vm_names.index(vm_name))]

    # do not run the policy simulation against more that 4 VMs
    try:
        vms.extend(all_vms[0:min(random.randint(1, len(all_vms)), 4)])
    except ValueError:
        pytest.skip("No other vms exist on provider to run policy simulation against.")

    filtered_collection = collection.filter({"names": [vm.name for vm in vms]})
    # Now perform the policy simulation
    view = navigate_to(filtered_collection, "PolicySimulation")
    # Select the correct policy profile
    view.fill({"form": {"policy_profile": "{}".format(vm_compliance_policy_profile.description)}})

    # Now check each quadicon and ensure that only cu-24x7 is compliant
    for entity in view.form.entities.get_all():
        state = entity.data["quad"]["bottomRight"]["tooltip"]
        if entity.name == vm_name:
            assert state == "Policy simulation successful."
        else:
            assert state == "Policy simulation failed with: false"


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1740290])
@pytest.mark.parametrize("page", ["ControlSimulation", "ControlImportExport", "ControlLog"],
                         ids=["Simulation", "ImportExport", "Log"])
def test_control_breadcrumbs(appliance, page):
    """
    Test to make sure breadcrumbs are visible and properly displayed

    Bugzilla:
        1740290

    Polarion:
        assignee: jdupuy
        caseimportance: high
        casecomponent: Control
        initialEstimate: 1/30h
        startsin: 5.11
    """
    # To properly test BZ 1740290, we must first navigate to ControlExplorer page
    view = navigate_to(appliance.server, "ControlExplorer")
    assert view.breadcrumb.locations == BREADCRUMB_LOCATIONS["ControlExplorer"]
    assert view.breadcrumb.is_displayed
    view = navigate_to(appliance.server, page)
    assert view.breadcrumb.is_displayed
    assert view.breadcrumb.locations == BREADCRUMB_LOCATIONS[page]
