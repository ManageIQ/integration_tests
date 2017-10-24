# -*- coding: utf-8 -*-
""" Tests checking the basic functionality of the Control/Explorer section.

Whether we can create/update/delete/assign/... these objects. Nothing with deep meaning.
Can be also used as a unit-test for page model coverage.

"""
from collections import namedtuple
import fauxfactory
import pytest
import random

from cfme.control.explorer import (actions, alert_profiles, alerts, conditions, policies,
    policy_profiles)

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.version import current_version
from cfme.utils.blockers import BZ
from cfme import test_requirements

pytestmark = [
    pytest.mark.long_running,
    test_requirements.control
]

EXPRESSIONS_TO_TEST = [
    (
        "Field",
        "fill_field({} : Last Compliance Timestamp, BEFORE, 03/04/2014)",
        '{} : Last Compliance Timestamp BEFORE "03/04/2014 00:00"'
    ),
    (
        "Count",
        "fill_count({}.Compliance History, >, 0)",
        'COUNT OF {}.Compliance History > 0'
    ),
    (
        "Tag",
        "fill_tag({}.User.My Company Tags : Location, Chicago)",
        "{}.User.My Company Tags : Location CONTAINS 'Chicago'"
    ),
    (
        "Find",
        "fill_find({}.Compliance History : Event Type, INCLUDES, some_string, Check Any,"
        "Resource Type, =, another_string)",
        'FIND {}.Compliance History : Event Type INCLUDES "some_string" CHECK ANY Resource Type'
        ' = "another_string"'
    )
]

COMPLIANCE_POLICIES = [
    policies.HostCompliancePolicy,
    policies.VMCompliancePolicy,
    policies.ReplicatorCompliancePolicy,
    policies.PodCompliancePolicy,
    policies.ContainerNodeCompliancePolicy,
    policies.ContainerImageCompliancePolicy,
]

CONTROL_POLICIES = [
    policies.HostControlPolicy,
    policies.VMControlPolicy,
    policies.ReplicatorControlPolicy,
    policies.PodControlPolicy,
    policies.ContainerNodeControlPolicy,
    policies.ContainerImageControlPolicy
]

POLICIES = COMPLIANCE_POLICIES + CONTROL_POLICIES

CONDITIONS = [
    conditions.HostCondition,
    conditions.VMCondition,
    conditions.ReplicatorCondition,
    conditions.PodCondition,
    conditions.ContainerNodeCondition,
    conditions.ContainerImageCondition,
    conditions.ProviderCondition
]

PolicyAndCondition = namedtuple('PolicyAndCondition', ['name', 'policy', 'condition'])
POLICIES_AND_CONDITIONS = [
    PolicyAndCondition(name=obj[0].__name__, policy=obj[0], condition=obj[1])
    for obj in zip(CONTROL_POLICIES, CONDITIONS)
]

EVENTS = [
    "Datastore Analysis Complete",
    "Datastore Analysis Request",
    "Host Auth Changed",
    "Host Auth Error",
    "Host Auth Incomplete Credentials",
    "Host Auth Invalid",
    "Host Auth Unreachable",
    "Host Auth Valid",
    "Provider Auth Changed",
    "Provider Auth Error",
    "Provider Auth Incomplete Credentials",
    "Provider Auth Invalid",
    "Provider Auth Unreachable",
    "Provider Auth Valid",
    "Tag Complete",
    "Tag Parent Cluster Complete",
    "Tag Parent Datastore Complete",
    "Tag Parent Host Complete",
    "Tag Parent Resource Pool Complete",
    "Tag Request",
    "Un-Tag Complete",
    "Un-Tag Parent Cluster Complete",
    "Un-Tag Parent Datastore Complete",
    "Un-Tag Parent Host Complete",
    "Un-Tag Parent Resource Pool Complete",
    "Un-Tag Request",
    "Container Image Compliance Failed",
    "Container Image Compliance Passed",
    "Container Node Compliance Failed",
    "Container Node Compliance Passed",
    "Host Compliance Failed",
    "Host Compliance Passed",
    "Pod Compliance Failed",
    "Pod Compliance Passed",
    "Replicator Compliance Failed",
    "Replicator Compliance Passed",
    "VM Compliance Failed",
    "VM Compliance Passed",
    "Container Image Analysis Complete",
    "Container Image Discovered",
    "Container Node Failed Mount",
    "Container Node Invalid Disk Capacity",
    "Container Node Not Ready",
    "Container Node Not Schedulable",
    "Container Node Ready",
    "Container Node Rebooted",
    "Container Node Schedulable",
    "Pod Deadline Exceeded",
    "Pod Failed Scheduling",
    "Pod Failed Sync",
    "Pod Failed Validation",
    "Pod Insufficient Free CPU",
    "Pod Insufficient Free Memory",
    "Pod Out of Disk",
    "Pod Scheduled",
    "Pod hostPort Conflict",
    "Pod nodeSelector Mismatching",
    "Replicator Failed Creating Pod",
    "Replicator Successfully Created Pod",
    "Host Added to Cluster",
    "Host Analysis Complete",
    "Host Analysis Request",
    "Host Connect",
    "Host Disconnect",
    "Host Maintenance Enter Request",
    "Host Maintenance Exit Request",
    "Host Provision Complete",
    "Host Reboot Request",
    "Host Removed from Cluster",
    "Host Reset Request",
    "Host Shutdown Request",
    "Host Standby Request",
    "Host Start Request",
    "Host Stop Request",
    "Host Vmotion Disable Request",
    "Host Vmotion Enable Request",
    "Service Provision Complete",
    "Service Retire Request",
    "Service Retired",
    "Service Retirement Warning",
    "Service Start Request",
    "Service Started",
    "Service Stop Request",
    "Service Stopped",
    "VM Clone Complete",
    "VM Clone Start",
    "VM Create Complete",
    "VM Delete (from Disk) Request",
    "VM Renamed Event",
    "VM Settings Change",
    "VM Template Create Complete",
    "VM Provision Complete",
    "VM Retire Request",
    "VM Retired",
    "VM Retirement Warning",
    "VM Analysis Complete",
    "VM Analysis Failure",
    "VM Analysis Request",
    "VM Analysis Start",
    "VM Guest Reboot",
    "VM Guest Reboot Request",
    "VM Guest Shutdown",
    "VM Guest Shutdown Request",
    "VM Live Migration (VMOTION)",
    "VM Pause",
    "VM Pause Request",
    "VM Power Off",
    "VM Power Off Request",
    "VM Power On",
    "VM Power On Request",
    "VM Remote Console Connected",
    "VM Removal from Inventory",
    "VM Removal from Inventory Request",
    "VM Reset",
    "VM Reset Request",
    "VM Resume",
    "VM Shelve",
    "VM Shelve Offload",
    "VM Shelve Offload Request",
    "VM Shelve Request",
    "VM Snapshot Create Complete",
    "VM Snapshot Create Request",
    "VM Snapshot Create Started",
    "VM Standby of Guest",
    "VM Standby of Guest Request",
    "VM Suspend",
    "VM Suspend Request"
]

ALERT_PROFILES = [
    alert_profiles.ClusterAlertProfile,
    alert_profiles.DatastoreAlertProfile,
    alert_profiles.HostAlertProfile,
    alert_profiles.MiddlewareServerAlertProfile,
    alert_profiles.ProviderAlertProfile,
    alert_profiles.ServerAlertProfile,
    alert_profiles.VMInstanceAlertProfile
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


@pytest.fixture(scope="module")
def alert_profile_collection(appliance):
    return appliance.collections.alert_profiles


@pytest.yield_fixture
def two_random_policies(policy_collection):
    policy_1 = policy_collection.create(
        random.choice(POLICIES),
        fauxfactory.gen_alphanumeric()
    )
    policy_2 = policy_collection.create(
        random.choice(POLICIES),
        fauxfactory.gen_alphanumeric()
    )
    yield policy_1, policy_2
    policy_collection.delete(policy_1, policy_2)


@pytest.fixture(params=POLICIES, ids=lambda policy_class: policy_class.__name__)
def policy_class(request):
    return request.param


@pytest.fixture(params=ALERT_PROFILES, ids=lambda alert_profile: alert_profile.__name__)
def alert_profile_class(request):
    return request.param


@pytest.yield_fixture
def policy(policy_collection, policy_class):
    policy_ = policy_collection.create(policy_class, fauxfactory.gen_alphanumeric())
    yield policy_
    policy_.delete()


@pytest.yield_fixture(params=CONDITIONS, ids=lambda condition_class: condition_class.__name__,
    scope="module")
def condition_for_expressions(request, condition_collection):
    condition_class = request.param
    condition = condition_collection.create(
        condition_class,
        fauxfactory.gen_alphanumeric(),
        expression="fill_field({} : Name, IS NOT EMPTY)".format(condition_class.FIELD_VALUE),
        scope="fill_field({} : Name, INCLUDES, {})".format(condition_class.FIELD_VALUE,
            fauxfactory.gen_alpha())
    )
    yield condition
    condition.delete()


@pytest.fixture(params=CONDITIONS, ids=lambda condition_class: condition_class.__name__)
def condition_prerequisites(request, condition_collection):
    condition_class = request.param
    expression = "fill_field({} : Name, =, {})".format(
        condition_class.FIELD_VALUE,
        fauxfactory.gen_alphanumeric()
    )
    scope = "fill_field({} : Name, =, {})".format(
        condition_class.FIELD_VALUE,
        fauxfactory.gen_alphanumeric()
    )
    return condition_class, scope, expression


@pytest.yield_fixture(params=CONTROL_POLICIES, ids=lambda policy_class: policy_class.__name__)
def control_policy(request, policy_collection):
    policy_class = request.param
    policy = policy_collection.create(policy_class, fauxfactory.gen_alphanumeric())
    yield policy
    policy.delete()


@pytest.yield_fixture
def action(action_collection):
    action_ = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )
    yield action_
    action_.delete()


@pytest.yield_fixture
def alert(alert_collection):
    alert_ = alert_collection.create(
        fauxfactory.gen_alphanumeric(),
        based_on=random.choice(ALERT_PROFILES).TYPE,
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    yield alert_
    alert_.delete()


@pytest.yield_fixture
def alert_profile(alert_profile_class, alert_collection, alert_profile_collection):
    alert = alert_collection.create(
        fauxfactory.gen_alphanumeric(),
        based_on=alert_profile_class.TYPE,
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    alert_profile_ = alert_profile_collection.create(
        alert_profile_class,
        fauxfactory.gen_alphanumeric(),
        alerts=[alert.description]
    )
    yield alert_profile_
    alert_profile_.delete()
    alert.delete()


@pytest.yield_fixture(params=POLICIES_AND_CONDITIONS, ids=lambda item: item.name)
def policy_and_condition(request, policy_collection, condition_collection):
    condition_class = request.param.condition
    policy_class = request.param.policy
    expression = "fill_field({} : Name, =, {})".format(
        condition_class.FIELD_VALUE,
        fauxfactory.gen_alphanumeric()
    )
    condition = condition_collection.create(
        condition_class,
        fauxfactory.gen_alphanumeric(),
        expression=expression
    )
    policy = policy_collection.create(
        policy_class,
        fauxfactory.gen_alphanumeric()
    )
    yield policy, condition
    policy.delete()
    condition.delete()


@pytest.mark.tier(2)
def test_condition_crud(condition_collection, condition_prerequisites):
    # CR
    condition_class, scope, expression = condition_prerequisites
    condition = condition_collection.create(
        condition_class,
        fauxfactory.gen_alphanumeric(),
        scope=scope,
        expression=expression
    )
    with update(condition):
        condition.notes = "Modified!"
    # D
    condition.delete()


@pytest.mark.tier(2)
def test_action_crud(action_collection):
    # CR
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )
    # U
    with update(action):
        action.description = "w00t w00t"
    # D
    action.delete()


@pytest.mark.tier(2)
def test_policy_crud(policy_collection, policy_class):
    # CR
    policy = policy_collection.create(policy_class, fauxfactory.gen_alphanumeric())
    # U
    with update(policy):
        policy.notes = "Modified!"
    # D
    policy.delete()


@pytest.mark.tier(3)
def test_policy_copy(policy):
    random_policy_copy = policy.copy()
    assert random_policy_copy.exists
    random_policy_copy.delete()


@pytest.mark.tier(3)
def test_assign_two_random_events_to_control_policy(control_policy, soft_assert):
    random_events = random.sample(EVENTS, 2)
    control_policy.assign_events(*random_events)
    soft_assert(control_policy.is_event_assigned(random_events[0]))
    soft_assert(control_policy.is_event_assigned(random_events[1]))


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1491576, forced_streams=["5.7.4"])])
def test_control_assign_actions_to_event(request, policy, action):
    if type(policy) in CONTROL_POLICIES:
        event = random.choice(EVENTS)
        policy.assign_events(event)
        request.addfinalizer(policy.assign_events)
    else:
        prefix = policy.TREE_NODE if not policy.TREE_NODE == "Vm" else policy.TREE_NODE.upper()
        event = "{} Compliance Check".format(prefix)
        request.addfinalizer(lambda: policy.assign_actions_to_event(
            event, {"Mark as Non-Compliant": False}))
    policy.assign_actions_to_event(event, action)
    assert str(action) == policy.assigned_actions_to_event(event)[0]


@pytest.mark.tier(3)
def test_assign_condition_to_control_policy(request, policy_and_condition):
    """This test checks if a condition is assigned to a control policy.
    Steps:
        * Create a control policy.
        * Assign a condition to the created policy.
    """
    policy, condition = policy_and_condition
    policy.assign_conditions(condition)
    request.addfinalizer(policy.assign_conditions)
    assert policy.is_condition_assigned(condition)


@pytest.mark.tier(2)
def test_policy_profile_crud(policy_profile_collection, two_random_policies):
    profile = policy_profile_collection.create(
        fauxfactory.gen_alphanumeric(),
        policies=two_random_policies
    )
    with update(profile):
        profile.notes = "Modified!"
    profile.delete()


@pytest.mark.tier(3)
@pytest.mark.parametrize("fill_type,expression,verify", EXPRESSIONS_TO_TEST, ids=[
    expr[0] for expr in EXPRESSIONS_TO_TEST])
def test_modify_condition_expression(condition_for_expressions, fill_type, expression, verify):
    with update(condition_for_expressions):
        condition_for_expressions.expression = expression.format(
            condition_for_expressions.FIELD_VALUE)
    assert condition_for_expressions.read_expression() == verify.format(
        condition_for_expressions.FIELD_VALUE)


@pytest.mark.tier(2)
def test_alert_crud(alert_collection):
    # CR
    alert = alert_collection.create(
        fauxfactory.gen_alphanumeric(),
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    # U
    with update(alert):
        alert.notification_frequency = "2 Hours"
    # D
    alert.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1303645], automates=[1303645])
def test_control_alert_copy(alert):
    alert_copy = alert.copy(description=fauxfactory.gen_alphanumeric())
    assert alert_copy.exists
    alert_copy.delete()


@pytest.mark.tier(2)
def test_alert_profile_crud(request, alert_profile_class, alert_collection,
        alert_profile_collection):
    alert = alert_collection.create(
        fauxfactory.gen_alphanumeric(),
        based_on=alert_profile_class.TYPE,
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    request.addfinalizer(alert.delete)
    alert_profile = alert_profile_collection.create(
        alert_profile_class,
        fauxfactory.gen_alphanumeric(),
        alerts=[alert.description]
    )
    with update(alert_profile):
        alert_profile.notes = "Modified!"
    alert_profile.delete()


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1416311, forced_streams=["5.7"])])
def test_alert_profile_assigning(alert_profile):
    if isinstance(alert_profile, alert_profiles.ServerAlertProfile):
        alert_profile.assign_to("Selected Servers", selections=["Servers", "EVM"])
    else:
        alert_profile.assign_to("The Enterprise")


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda: current_version() < "5.8")
def test_control_is_ansible_playbook_available_in_actions_dropdown(action_collection):
    view = navigate_to(action_collection, "Add")
    assert "Run Ansible Playbook" in [option.text for option in view.action_type.all_options]
