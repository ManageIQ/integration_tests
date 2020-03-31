""" Tests checking the basic functionality of the Control/Explorer section.

Whether we can create/update/delete/assign/... these objects. Nothing with deep meaning.
Can be also used as a unit-test for page model coverage.

"""
import random
from collections import namedtuple

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.control.explorer import alert_profiles
from cfme.control.explorer import conditions
from cfme.control.explorer import policies
from cfme.control.explorer.alert_profiles import AlertProfileDetailsView
from cfme.control.explorer.policies import EditPolicyEventAssignments
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    test_requirements.control,
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
    policies.ProviderCompliancePolicy,
    policies.PhysicalInfrastructureCompliancePolicy
]

CONTROL_POLICIES = [
    policies.HostControlPolicy,
    policies.VMControlPolicy,
    policies.ReplicatorControlPolicy,
    policies.PodControlPolicy,
    policies.ContainerNodeControlPolicy,
    policies.ContainerImageControlPolicy,
    policies.ProviderControlPolicy,
    policies.PhysicalInfrastructureControlPolicy
]

POLICIES = COMPLIANCE_POLICIES + CONTROL_POLICIES
PHYS_POLICIES = (
    policies.PhysicalInfrastructureCompliancePolicy,
    policies.PhysicalInfrastructureControlPolicy
)

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
    'Login failed',
    'Host Auth Changed',
    'Host Auth Error',
    'Host Auth Incomplete Credentials',
    'Host Auth Invalid',
    'Host Auth Unreachable',
    'Host Auth Valid',
    'Provider Auth Changed',
    'Provider Auth Error',
    'Provider Auth Incomplete Credentials',
    'Provider Auth Invalid',
    'Provider Auth Unreachable',
    'Provider Auth Valid',
    'Tag Complete',
    'Tag Parent Cluster Complete',
    'Tag Parent Datastore Complete',
    'Tag Parent Host Complete',
    'Tag Parent Resource Pool Complete',
    'Tag Request',
    'Un-Tag Complete',
    'Un-Tag Parent Cluster Complete',
    'Un-Tag Parent Datastore Complete',
    'Un-Tag Parent Host Complete',
    'Un-Tag Parent Resource Pool Complete',
    'Un-Tag Request',
    'Container Image Compliance Failed',
    'Container Image Compliance Passed',
    'Container Node Compliance Failed',
    'Container Node Compliance Passed',
    'Host Compliance Failed',
    'Host Compliance Passed',
    'Pod Compliance Failed',
    'Pod Compliance Passed',
    'Provider Compliance Failed',
    'Provider Compliance Passed',
    'Replicator Compliance Failed',
    'Replicator Compliance Passed',
    'VM Compliance Failed',
    'VM Compliance Passed',
    'Container Image Analysis Complete',
    'Container Image Analysis Failure',
    'Container Image Analysis Request',
    'Container Image Discovered',
    'Container Node Failed Mount',
    'Container Node Invalid Disk Capacity',
    'Container Node Not Ready',
    'Container Node Not Schedulable',
    'Container Node Ready',
    'Container Node Rebooted',
    'Container Node Schedulable',
    'Container Project Discovered',
    'Pod Container Created',
    'Pod Container Failed',
    'Pod Container Killing',
    'Pod Container Started',
    'Pod Container Stopped',
    'Pod Container Unhealthy',
    'Pod Deadline Exceeded',
    'Pod Failed Scheduling',
    'Pod Failed Validation',
    'Pod Insufficient Free CPU',
    'Pod Insufficient Free Memory',
    'Pod Out of Disk',
    'Pod Scheduled',
    'Pod hostPort Conflict',
    'Pod nodeSelector Mismatching',
    'Replicator Failed Creating Pod',
    'Replicator Successfully Created Pod',
    'Database Failover Executed',
    'Datastore Analysis Complete',
    'Datastore Analysis Request',
    'Host Added to Cluster',
    'Host Analysis Complete',
    'Host Analysis Request',
    'Host Connect',
    'Host Disconnect',
    'Host Failure',
    'Host Maintenance Enter Request',
    'Host Maintenance Exit Request',
    'Host Reboot Request',
    'Host Removed from Cluster',
    'Host Reset Request',
    'Host Shutdown Request',
    'Host Standby Request',
    'Host Start Request',
    'Host Stop Request',
    'Host Vmotion Disable Request',
    'Host Vmotion Enable Request',
    'Orchestration Stack Retire Request',
    'Physical Server Reset',
    'Physical Server Shutdown',
    'Physical Server Start',
    'Service Provision Complete',
    'Service Retire Request',
    'Service Retired',
    'Service Retirement Warning',
    'Service Start Request',
    'Service Started',
    'Service Stop Request',
    'Service Stopped',
    'VM Renamed Event',
    'VM Settings Change',
    'VM Create Complete',
    'VM Delete (from Disk)',
    'VM Delete (from Disk) Request',
    'VM Provision Complete',
    'VM Retire Request',
    'VM Retired',
    'VM Retirement Warning',
    'VM Template Create Complete',
    'VM Analysis Complete',
    'VM Analysis Failure',
    'VM Analysis Request',
    'VM Analysis Start',
    'VM Clone Complete',
    'VM Clone Start',
    'VM Guest Reboot',
    'VM Guest Reboot Request',
    'VM Guest Shutdown',
    'VM Guest Shutdown Request',
    'VM Live Migration (VMOTION)',
    'VM Pause',
    'VM Pause Request',
    'VM Power Off',
    'VM Power Off Request',
    'VM Power On',
    'VM Power On Request',
    'VM Remote Console Connected',
    'VM Removal from Inventory',
    'VM Removal from Inventory Request',
    'VM Reset',
    'VM Reset Request',
    'VM Resume',
    'VM Shelve',
    'VM Shelve Offload',
    'VM Shelve Offload Request',
    'VM Shelve Request',
    'VM Snapshot Create Complete',
    'VM Snapshot Create Request',
    'VM Snapshot Create Started',
    'VM Standby of Guest',
    'VM Standby of Guest Request',
    'VM Suspend',
    'VM Suspend Request'
]

ALERT_PROFILES = [
    alert_profiles.ClusterAlertProfile,
    alert_profiles.DatastoreAlertProfile,
    alert_profiles.HostAlertProfile,
    alert_profiles.ProviderAlertProfile,
    alert_profiles.ServerAlertProfile,
    alert_profiles.VMInstanceAlertProfile
]


@pytest.fixture
def two_random_policies(appliance):
    # Physical Infrastucture policies excluded
    policy_collection = appliance.collections.policies
    policies = POLICIES
    policy_1 = policy_collection.create(
        random.choice(policies),
        fauxfactory.gen_alphanumeric()
    )
    policy_2 = policy_collection.create(
        random.choice(policies),
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


@pytest.fixture
def policy(appliance, policy_class):

    policy_ = appliance.collections.policies.create(policy_class, fauxfactory.gen_alphanumeric())
    yield policy_
    policy_.delete()


@pytest.fixture
def policy_for_event_test(appliance):

    policy_ = appliance.collections.policies.create(
        policies.VMControlPolicy,
        fauxfactory.gen_alphanumeric()
    )
    yield policy_
    policy_.delete()


@pytest.fixture(params=CONDITIONS, ids=lambda condition_class: condition_class.__name__,
    scope="module")
def condition_for_expressions(request, appliance):
    condition_class = request.param
    condition = appliance.collections.conditions.create(
        condition_class,
        fauxfactory.gen_alphanumeric(),
        expression="fill_field({} : Name, IS NOT EMPTY)".format(
            condition_class.FIELD_VALUE),
        scope="fill_field({} : Name, INCLUDES, {})".format(
            condition_class.FIELD_VALUE, fauxfactory.gen_alpha())
    )
    yield condition
    condition.delete()


@pytest.fixture(params=CONDITIONS, ids=lambda condition_class: condition_class.__name__)
def condition_prerequisites(request, appliance):
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


@pytest.fixture(params=CONTROL_POLICIES, ids=lambda policy_class: policy_class.__name__)
def control_policy_class(request):
    return request.param


@pytest.fixture
def control_policy(appliance, control_policy_class):
    policy = appliance.collections.policies.create(
        control_policy_class, fauxfactory.gen_alphanumeric()
    )
    yield policy
    policy.delete()


@pytest.fixture
def action(appliance):
    action_ = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )
    yield action_
    action_.delete()


@pytest.fixture
def alert(appliance):
    alert_ = appliance.collections.alerts.create(
        fauxfactory.gen_alphanumeric(),
        based_on=random.choice(ALERT_PROFILES).TYPE,
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    yield alert_
    alert_.delete()


@pytest.fixture
def alert_profile(appliance, alert_profile_class):
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alphanumeric(),
        based_on=alert_profile_class.TYPE,
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    alert_profile_ = appliance.collections.alert_profiles.create(
        alert_profile_class,
        fauxfactory.gen_alphanumeric(),
        alerts=[alert.description]
    )
    yield alert_profile_
    alert_profile_.delete()
    alert.delete()


@pytest.fixture(params=POLICIES_AND_CONDITIONS, ids=lambda item: item.name)
def policy_and_condition(request, appliance):
    condition_class = request.param.condition
    policy_class = request.param.policy
    expression = "fill_field({} : Name, =, {})".format(
        condition_class.FIELD_VALUE,
        fauxfactory.gen_alphanumeric()
    )
    condition = appliance.collections.conditions.create(
        condition_class,
        fauxfactory.gen_alphanumeric(),
        expression=expression
    )
    policy = appliance.collections.policies.create(
        policy_class,
        fauxfactory.gen_alphanumeric()
    )
    yield policy, condition
    policy.delete_if_exists()
    condition.delete_if_exists()


@pytest.fixture
def setup_for_monitor_alerts(appliance):
    """ Insert a fired alert into the db if none is present. This is done
        for tests involving the Monitor->Alerts pages.
    """
    query_str = "SELECT * FROM miq_alert_statuses"
    delete_str = "DELETE FROM miq_alert_statuses"

    # first we get rid of all fired alerts that may still be on an appliance
    if appliance.db.client.engine.execute(query_str).rowcount > 0:
        logger.info('Deleting all fired alerts from the appliance.')
        appliance.db.engine.execute(delete_str)

    # first get the ems_id for the provider
    table = appliance.db.client['ems_clusters']
    ems_id_column = getattr(table, 'ems_id')
    ems_id = appliance.db.client.session.query(ems_id_column)[0].ems_id

    logger.info('Injecting a fired alert into the appliance DB.')

    description = 'a fake fired alert'

    insert_str = (
        "INSERT INTO miq_alert_statuses "
        "(id, miq_alert_id, resource_id, resource_type, result, description, ems_id)"
        " VALUES ('100', '1', '1', 'VmOrTemplate', 'f', '{}', '{}')"
    ).format(description, int(ems_id))
    delete_str += " WHERE id='100'"

    # create the fired alert
    appliance.db.client.engine.execute(insert_str)
    yield description
    # delete at end of test
    logger.info('Deleting fired alert from appliance DB.')
    appliance.db.client.engine.execute(delete_str)


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_condition_crud(appliance, condition_prerequisites):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h
    """
    # CR
    condition_class, scope, expression = condition_prerequisites
    condition = appliance.collections.conditions.create(
        condition_class,
        fauxfactory.gen_alphanumeric(),
        scope=scope,
        expression=expression
    )
    with update(condition):
        condition.notes = "Modified!"
    # D
    condition.delete()


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_action_crud(appliance):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: critical
        initialEstimate: 1/12h
    """
    # CR
    action = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )
    # U
    with update(action):
        action.description = "w00t w00t"
    # D
    action.delete()


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_policy_crud(appliance, policy_class):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/4h
    """
    # CR
    policy = appliance.collections.policies.create(policy_class, fauxfactory.gen_alphanumeric())
    # U
    with update(policy):
        policy.notes = "Modified!"
    # D
    policy.delete()


@pytest.mark.tier(3)
def test_policy_copy(policy_class, policy):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h
    """
    random_policy_copy = policy.copy()
    assert random_policy_copy.exists
    random_policy_copy.delete()


@pytest.mark.tier(3)
def test_assign_two_random_events_to_control_policy(control_policy, control_policy_class,
                                                    soft_assert):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/4h
    """
    random_events = random.sample(EVENTS, 2)
    control_policy.assign_events(*random_events)
    soft_assert(control_policy.is_event_assigned(random_events[0]))
    soft_assert(control_policy.is_event_assigned(random_events[1]))


@pytest.mark.tier(2)
def test_control_assign_actions_to_event(request, policy_class, policy, action):
    """
    Bugzilla:
        1700070

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: critical
        initialEstimate: 1/12h
    """
    if type(policy) in CONTROL_POLICIES:
        event = random.choice(EVENTS)
        policy.assign_events(event)

        @request.addfinalizer
        def _cleanup():
            policy.unassign_events(event)
    else:
        prefix = policy.TREE_NODE if not policy.TREE_NODE == "Vm" else policy.TREE_NODE.upper()
        if policy.TREE_NODE == "Physical Infrastructure" and BZ(1700070).blocks:
            prefix = policy.PRETTY
        event = f"{prefix} Compliance Check"
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

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h
    """
    policy, condition = policy_and_condition
    policy.assign_conditions(condition)
    request.addfinalizer(policy.assign_conditions)
    assert policy.is_condition_assigned(condition)


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_policy_profile_crud(appliance, two_random_policies):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: critical
        initialEstimate: 1/12h
    """
    profile = appliance.collections.policy_profiles.create(
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
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: low
        initialEstimate: 1/12h
    """
    with update(condition_for_expressions):
        condition_for_expressions.expression = expression.format(
            condition_for_expressions.FIELD_VALUE)
    assert condition_for_expressions.read_expression() == verify.format(
        condition_for_expressions.FIELD_VALUE)


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_alert_crud(appliance):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/12h
    """
    # CR
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alphanumeric()
    )
    # U
    with update(alert):
        alert.notification_frequency = "2 Hours"
    # D
    alert.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1303645])
def test_control_alert_copy(alert):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h
    """
    alert_copy = alert.copy(description=fauxfactory.gen_alphanumeric())
    assert alert_copy.exists
    alert_copy.delete()


@pytest.mark.sauce
@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1723815)], automates=[BZ(1723815)])
def test_alert_profile_crud(request, appliance, alert_profile_class):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: critical
        initialEstimate: 1/12h

    Bugzilla:
        1723815
    """
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alphanumeric(),
        based_on=alert_profile_class.TYPE,
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    request.addfinalizer(alert.delete)
    alert_profile = appliance.collections.alert_profiles.create(
        alert_profile_class,
        fauxfactory.gen_alphanumeric(),
        alerts=[alert.description]
    )
    with update(alert_profile):
        alert_profile.notes = "Modified!"
    alert_profile.delete()


@pytest.mark.tier(2)
def test_alert_profile_assigning(alert_profile, appliance):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/12h
    """
    view = appliance.browser.create_view(AlertProfileDetailsView)
    if isinstance(alert_profile, alert_profiles.ServerAlertProfile):
        options = dict(assign='Selected Servers', selections=['Servers', 'EVM'])
    else:
        options = dict(assign='The Enterprise')

    # first assignment should be unique
    first_change = alert_profile.assign_to(**options)
    assert first_change
    view.flash.assert_success_message('Alert Profile "{}" assignments successfully saved'
                                      .format(alert_profile.description))

    # second assignment, no change, should be cancelled
    second_change = alert_profile.assign_to(**options)
    assert not second_change
    view.flash.assert_success_message('Edit Alert Profile assignments cancelled by user')


@pytest.mark.tier(2)
def test_control_is_ansible_playbook_available_in_actions_dropdown(appliance):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/12h
    """
    view = navigate_to(appliance.collections.actions, "Add")
    assert "Run Ansible Playbook" in [option.text for option in view.action_type.all_options]


@pytest.mark.tier(2)
def test_alerts_monitor_overview_page(appliance, virtualcenter_provider, setup_for_monitor_alerts):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h
    """

    view = navigate_to(appliance.collections.alerts, 'MonitorOverview')

    # 1) assert that the status card displays the correct information
    status_card = view.status_card(virtualcenter_provider.name)
    wait_for(
        func=lambda: int(status_card.notifications[0].text) == 1, num_sec=20, handle_exception=True
    )

    # 2) assert that clicking the status card navigates to the correct place
    status_card.click()
    assert view.navigation.currently_selected == ['Monitor', 'Alerts', 'All Alerts']


def test_default_policy_events(policy_for_event_test, soft_assert):
    """
    Test to ensure that the events listed on the Event Assignment page for policies do not change

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/12h
    """
    view = navigate_to(policy_for_event_test, "Details")
    view.configuration.item_select("Edit this Policy's Event assignments")
    view = policy_for_event_test.create_view(EditPolicyEventAssignments)
    # assert that the string of events is the same as the hardcoded ones above
    soft_assert(sorted(view.events.all_labels) == sorted(EVENTS), "Policy events do not match!")
    # click cancel button so we aren't stuck on this page
    view.cancel_button.click()
