# -*- coding: utf-8 -*-
""" Tests checking the basic functionality of the Control/Explorer section.

Whether we can create/update/delete/assign/... these objects. Nothing with deep meaning.
Can be also used as a unit-test for page model coverage.

TODO: * Multiple expression types entering. (extend the update tests)
"""
import fauxfactory
import pytest

import cfme.fixtures.pytest_selenium as sel

from cfme.control import explorer
from utils.update import update
from utils.version import current_version
from cfme.web_ui import flash
from cfme.web_ui import expression_editor

pytestmark = [pytest.mark.long_running]

VM_EXPRESSIONS_TO_TEST = [
    (
        "fill_field(VM and Instance : Boot Time, BEFORE, Today)",
        'VM and Instance : Boot Time BEFORE "Today"'
    ),
    (
        "fill_field(VM and Instance : Boot Time, BEFORE, 03/04/2014)",
        'VM and Instance : Boot Time BEFORE "03/04/2014 00:00"'
    ),
    (
        "fill_field(VM and Instance : Custom 6, RUBY, puts 'hello')",
        'VM and Instance : Custom 6 RUBY <RUBY Expression>'
    ),
    (
        "fill_field(VM and Instance : Format, IS NOT NULL)",
        'VM and Instance : Format IS NOT NULL'
    ),
    (
        "fill_count(VM and Instance.Files, =, 150)",
        'COUNT OF VM and Instance.Files = 150'
    ),
    # ("fill_tag(VM and Instance.My Company Tags : Owner, Production Linux Team)",)
    # Needs working input/select mutability
]


@pytest.yield_fixture
def random_alert():
    alert = explorer.Alert(
        fauxfactory.gen_alphanumeric(), timeline_event=True, driving_event="Hourly Timer"
    )
    alert.create()
    yield alert
    alert.delete()


@pytest.yield_fixture(params=[explorer.VMCompliancePolicy,
                              explorer.HostCompliancePolicy,
                              explorer.HostControlPolicy,
                              explorer.VMControlPolicy],
                      ids=["VMCompliancePolicy",
                           "HostCompliancePolicy",
                           "HostControlPolicy",
                           "VMControlPolicy"])
def random_policy(request):
    policy = request.param(fauxfactory.gen_alphanumeric())
    policy.create()
    yield policy
    policy.delete()


@pytest.yield_fixture(scope="module")
def vm_condition_for_expressions():
    cond = explorer.VMCondition(
        fauxfactory.gen_alphanumeric(),
        expression="fill_field(VM and Instance : CPU Limit, =, 20)",
        scope="fill_count(VM and Instance.Files, >, 150)"
    )
    cond.create()
    yield cond
    cond.delete()


@pytest.yield_fixture
def random_vm_condition():
    cond = explorer.VMCondition(
        fauxfactory.gen_alphanumeric(),
        expression="fill_field(VM and Instance : CPU Limit, =, 20)",
        scope="fill_count(VM and Instance.Files, >, 150)"
    )
    cond.create()
    yield cond
    cond.delete()


@pytest.yield_fixture
def random_host_condition():
    expression = "fill_count(Host / Node.Files, >, 150)"
    cond = explorer.HostCondition(
        fauxfactory.gen_alphanumeric(),
        expression=expression,
    )
    cond.create()
    yield cond
    cond.delete()


@pytest.yield_fixture
def random_vm_control_policy():
    policy = explorer.VMControlPolicy(fauxfactory.gen_alphanumeric())
    policy.create()
    yield policy
    policy.delete()


@pytest.yield_fixture
def random_host_control_policy():
    policy = explorer.HostControlPolicy(fauxfactory.gen_alphanumeric())
    policy.create()
    yield policy
    policy.delete()


@pytest.yield_fixture(params=[explorer.ClusterAlertProfile,
                              explorer.DatastoreAlertProfile,
                              explorer.HostAlertProfile,
                              explorer.ProviderAlertProfile,
                              explorer.ServerAlertProfile,
                              explorer.VMInstanceAlertProfile],
                      ids=[explorer.ClusterAlertProfile.TYPE,
                           explorer.DatastoreAlertProfile.TYPE,
                           explorer.HostAlertProfile.TYPE,
                           explorer.ProviderAlertProfile.TYPE,
                           explorer.ServerAlertProfile.TYPE,
                           explorer.VMInstanceAlertProfile.TYPE])
def alert_profile(request):
    alert = explorer.Alert(
        fauxfactory.gen_alphanumeric(),
        based_on=request.param.TYPE,
        timeline_event=True,
        driving_event="Hourly Timer"
    )
    alert.create()
    alert_profile = request.param(fauxfactory.gen_alphanumeric(), [alert])
    yield alert_profile
    alert.delete()


def test_vm_condition_crud(soft_assert):
    condition = explorer.VMCondition(
        fauxfactory.gen_alphanumeric(),
        expression="fill_field(VM and Instance : CPU Limit, =, 20)",
        scope="fill_count(VM and Instance.Files, >, 150)"
    )
    # CR
    condition.create()
    soft_assert(condition.exists, "The condition {} does not exist!".format(
        condition.description
    ))
    # U
    with update(condition):
        condition.notes = "Modified!"
    sel.force_navigate("vm_condition_edit", context={"condition_name": condition.description})
    soft_assert(sel.text(condition.form.notes).strip() == "Modified!", "Modification failed!")
    # D
    condition.delete()
    soft_assert(not condition.exists, "The condition {} exists!".format(
        condition.description
    ))


def test_host_condition_crud(soft_assert):
    expression = "fill_count(Host / Node.Files, >, 150)"
    condition = explorer.HostCondition(
        fauxfactory.gen_alphanumeric(),
        expression=expression
    )
    # CR
    condition.create()
    soft_assert(condition.exists, "The condition {} does not exist!".format(
        condition.description
    ))
    # U
    with update(condition):
        condition.notes = "Modified!"
    sel.force_navigate("host_condition_edit", context={"condition_name": condition.description})
    soft_assert(sel.text(condition.form.notes).strip() == "Modified!", "Modification failed!")
    # D
    condition.delete()
    soft_assert(not condition.exists, "The condition {} exists!".format(
        condition.description
    ))


def test_action_crud(soft_assert):
    action = explorer.Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )
    # CR
    action.create()
    soft_assert(action.exists, "The action {} does not exist!".format(
        action.description
    ))
    # U
    with update(action):
        action.description = "w00t w00t"
    sel.force_navigate("control_explorer_action_edit", context={"action_name": action.description})
    soft_assert(
        sel.get_attribute(action.form.description, "value").strip() == "w00t w00t",
        "Modification failed!"
    )
    # D
    action.delete()
    soft_assert(not action.exists, "The action {} exists!".format(
        action.description
    ))


def test_vm_control_policy_crud(soft_assert):
    policy = explorer.VMControlPolicy(fauxfactory.gen_alphanumeric())
    # CR
    policy.create()
    soft_assert(policy.exists, "The policy {} does not exist!".format(
        policy.description
    ))
    # U
    with update(policy):
        policy.notes = "Modified!"
    sel.force_navigate("vm_control_policy_edit", context={"policy_name": policy.description})
    soft_assert(sel.text(policy.form.notes).strip() == "Modified!", "Modification failed!")
    # D
    policy.delete()
    soft_assert(not policy.exists, "The policy {} exists!".format(
        policy.description
    ))


def test_vm_compliance_policy_crud(soft_assert):
    policy = explorer.VMCompliancePolicy(fauxfactory.gen_alphanumeric())
    # CR
    policy.create()
    soft_assert(policy.exists, "The policy {} does not exist!".format(
        policy.description
    ))
    # U
    with update(policy):
        policy.notes = "Modified!"
    sel.force_navigate("vm_compliance_policy_edit", context={"policy_name": policy.description})
    soft_assert(sel.text(policy.form.notes).strip() == "Modified!", "Modification failed!")
    # D
    policy.delete()
    soft_assert(not policy.exists, "The policy {} exists!".format(
        policy.description
    ))


def test_host_control_policy_crud(soft_assert):
    policy = explorer.HostControlPolicy(fauxfactory.gen_alphanumeric())
    # CR
    policy.create()
    soft_assert(policy.exists, "The policy {} does not exist!".format(
        policy.description
    ))
    # U
    with update(policy):
        policy.notes = "Modified!"
    sel.force_navigate("host_control_policy_edit", context={"policy_name": policy.description})
    soft_assert(sel.text(policy.form.notes).strip() == "Modified!", "Modification failed!")
    # D
    policy.delete()
    soft_assert(not policy.exists, "The policy {} exists!".format(
        policy.description
    ))


def test_host_compliance_policy_crud(soft_assert):
    policy = explorer.HostCompliancePolicy(fauxfactory.gen_alphanumeric())
    # CR
    policy.create()
    soft_assert(policy.exists, "The policy {} does not exist!".format(
        policy.description
    ))
    # U
    with update(policy):
        policy.notes = "Modified!"
    sel.force_navigate("host_compliance_policy_edit", context={"policy_name": policy.description})
    soft_assert(sel.text(policy.form.notes).strip() == "Modified!", "Modification failed!")
    # D
    policy.delete()
    soft_assert(not policy.exists, "The policy {} exists!".format(
        policy.description
    ))


def test_policies_copy(random_policy, soft_assert):
    random_policy_copy = random_policy.copy()
    soft_assert(random_policy_copy.exists, "The {} does not exist!".format(random_policy_copy))
    random_policy_copy.delete()


def test_assign_events_to_vm_control_policy(random_vm_control_policy, soft_assert):
    random_vm_control_policy.assign_events("VM Retired", "VM Clone Start")
    soft_assert(random_vm_control_policy.is_event_assigned("VM Retired"))
    soft_assert(random_vm_control_policy.is_event_assigned("VM Clone Start"))


def test_assign_events_to_host_control_policy(random_host_control_policy, soft_assert):
    random_host_control_policy.assign_events("Host Auth Error", "Host Compliance Passed")
    soft_assert(random_host_control_policy.is_event_assigned("Host Auth Error"))
    soft_assert(random_host_control_policy.is_event_assigned("Host Compliance Passed"))


def test_assign_vm_condition_to_vm_policy(
        random_vm_control_policy, random_vm_condition, soft_assert):
    random_vm_control_policy.assign_conditions(random_vm_condition)
    soft_assert(random_vm_control_policy.is_condition_assigned(random_vm_condition))
    random_vm_control_policy.assign_conditions()  # unassign


def test_assign_host_condition_to_host_policy(
        random_host_control_policy, random_host_condition, soft_assert):
    random_host_control_policy.assign_conditions(random_host_condition)
    soft_assert(random_host_control_policy.is_condition_assigned(random_host_condition))
    random_host_control_policy.assign_conditions()  # unassign


def test_policy_profile_crud(random_vm_control_policy, random_host_control_policy, soft_assert):
    profile = explorer.PolicyProfile(
        fauxfactory.gen_alphanumeric(),
        policies=[random_vm_control_policy, random_host_control_policy]
    )
    profile.create()
    soft_assert(profile.exists, "Policy profile {} does not exist!".format(profile.description))
    with update(profile):
        profile.notes = "Modified!"
    sel.force_navigate("policy_profile", context={"policy_profile_name": profile.description})
    soft_assert(sel.text(profile.form.notes).strip() == "Modified!")
    profile.delete()
    soft_assert(not profile.exists, "The policy profile {} exists!".format(profile.description))


# RUBY expression type is no longer supported.
@pytest.mark.uncollectif(lambda expression: "RUBY" in expression and current_version() >= "5.5")
@pytest.mark.parametrize(("expression", "verify"), VM_EXPRESSIONS_TO_TEST)
def test_modify_vm_condition_expression(
        vm_condition_for_expressions, expression, verify, soft_assert):
    with update(vm_condition_for_expressions):
        vm_condition_for_expressions.expression = expression
    flash.assert_no_errors()
    if verify is not None:
        sel.force_navigate("vm_condition_edit",
                           context={"condition_name": vm_condition_for_expressions.description})
        vm_condition_for_expressions.form.expression.show_func()
        soft_assert(expression_editor.get_expression_as_text() == verify)


def test_alert_crud(soft_assert):
    alert = explorer.Alert(
        fauxfactory.gen_alphanumeric(), timeline_event=True, driving_event="Hourly Timer"
    )
    # CR
    alert.create()
    soft_assert(alert.exists, "The alert {} does not exist!".format(
        alert.description
    ))
    # U
    with update(alert):
        alert.notification_frequency = "2 Hours"
    sel.force_navigate("control_explorer_alert_edit", context={"alert_name": alert.description})
    soft_assert(
        sel.text(
            alert.form.notification_frequency.first_selected_option
        ).strip() == "2 Hours", "Modification failed!"
    )
    # D
    alert.delete()
    soft_assert(not alert.exists, "The alert {} exists!".format(
        alert.description
    ))


@pytest.mark.meta(blockers=[1303645], automates=[1303645])
def test_control_alert_copy(random_alert, soft_assert):
    alert_copy = random_alert.copy()
    soft_assert(alert_copy.exists, "The alert {} does not exist!".format(
        alert_copy.description
    ))
    alert_copy.delete()
    soft_assert(not alert_copy.exists, "The alert {} exists!".format(
        alert_copy.description
    ))


def test_alert_profile_crud(alert_profile, soft_assert):
    alert_profile.create()
    soft_assert(alert_profile.exists, "The alert profile {} does not exist!".format(
        alert_profile.description
    ))
    with update(alert_profile):
        alert_profile.notes = "Modified!"
    sel.force_navigate("{}_alert_profile_edit".format(alert_profile.PREFIX),
                       context={"alert_profile_name": alert_profile.description})
    soft_assert(
        sel.text(
            alert_profile.form.notes) == "Modified!", "Modification failed!"
    )
    alert_profile.delete()
    soft_assert(not alert_profile.exists, "The alert profile {} exists!".format(
        alert_profile.description
    ))
