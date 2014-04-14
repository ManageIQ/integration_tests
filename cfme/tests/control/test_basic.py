#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""" Tests checking the basic functionality of the Control/Explorer section.

Whether we can create/update/delete/assign/... these objects. Nothing with deep meaning.
Can be also used as a unit-test for page model coverage.

Todo:
    * Multiple expression types entering. (extend the update tests)
"""

import pytest

import cfme.fixtures.pytest_selenium as sel

from cfme.control import explorer
from utils import randomness
from utils.update import update
from cfme.web_ui import flash
from cfme.web_ui import expression_editor

profile = None


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
    #("fill_tag(VM and Instance.My Company Tags : Owner, Production Linux Team)",)
    # Needs working input/select mutability
]


@pytest.fixture(scope="module")
def random_vm_condition_name():
    return randomness.generate_random_string()


@pytest.fixture(scope="module")
def random_vm_condition(random_vm_condition_name):
    return explorer.VMCondition(
        random_vm_condition_name,
        expression="fill_field(VM and Instance : CPU Limit, =, 20)",
        scope="fill_count(VM and Instance.Files, >, 150)"
    )


@pytest.fixture(scope="module")
def random_host_condition_name():
    return randomness.generate_random_string()


@pytest.fixture(scope="module")
def random_host_condition(random_host_condition_name):
    return explorer.HostCondition(
        random_host_condition_name,
        expression="fill_count(Host.Files, >, 150)"
    )


@pytest.fixture(scope="module")
def random_alert_name():
    return randomness.generate_random_string()


@pytest.fixture(scope="module")
def random_alert(random_alert_name):
    return explorer.Alert(random_alert_name, timeline_event=True, driving_event="Hourly Timer")

@pytest.fixture(scope="module")
def random_action_name():
    return randomness.generate_random_string()


@pytest.fixture(scope="module")
def random_action(random_action_name):
    return explorer.Action(
        random_action_name,
        action_type="Tag",
        action_values={"tag": ("My Company Tags", "Department", "Accounting")}
    )


@pytest.fixture(scope="module")
def random_vm_control_policy_name():
    return randomness.generate_random_string()


@pytest.fixture(scope="module")
def random_vm_control_policy(random_vm_control_policy_name):
    return explorer.VMControlPolicy(random_vm_control_policy_name)


@pytest.fixture(scope="module")
def random_host_control_policy_name():
    return randomness.generate_random_string()


@pytest.fixture(scope="module")
def random_host_control_policy(random_host_control_policy_name):
    return explorer.HostControlPolicy(random_host_control_policy_name)


def test_create_vm_condition(random_vm_condition):
    random_vm_condition.create()
    flash.assert_no_errors()
    assert random_vm_condition.exists


def test_create_host_condition(random_host_condition):
    random_host_condition.create()
    flash.assert_no_errors()
    assert random_host_condition.exists


def test_create_action(random_action):
    random_action.create()
    flash.assert_no_errors()
    assert random_action.exists


def test_create_vm_control_policy(random_vm_control_policy):
    random_vm_control_policy.create()
    flash.assert_no_errors()
    assert random_vm_control_policy.exists


def test_assign_events_to_vm_control_policy(random_vm_control_policy):
    random_vm_control_policy.assign_events("VM Retired", "VM Clone Start")
    flash.assert_no_errors()
    assert random_vm_control_policy.is_event_assigned("VM Retired")
    assert random_vm_control_policy.is_event_assigned("VM Clone Start")


def test_create_host_control_policy(random_host_control_policy):
    random_host_control_policy.create()
    flash.assert_no_errors()
    assert random_host_control_policy.exists


def test_assign_events_to_host_control_policy(random_host_control_policy):
    random_host_control_policy.assign_events("Host Auth Error", "Host Compliance Passed")
    flash.assert_no_errors()
    assert random_host_control_policy.is_event_assigned("Host Auth Error")
    assert random_host_control_policy.is_event_assigned("Host Compliance Passed")


def test_assign_vm_condition_to_vm_policy(random_vm_control_policy, random_vm_condition):
    random_vm_control_policy.assign_conditions(random_vm_condition)
    flash.assert_no_errors()
    assert random_vm_control_policy.is_condition_assigned(random_vm_condition)


def test_assign_host_condition_to_host_policy(random_host_control_policy, random_host_condition):
    random_host_control_policy.assign_conditions(random_host_condition)
    flash.assert_no_errors()
    assert random_host_control_policy.is_condition_assigned(random_host_condition)


@pytest.fixture(scope="module")
def random_policy_profile_name():
    return randomness.generate_random_string()


@pytest.mark.requires("test_create_vm_control_policy")
@pytest.mark.requires("test_create_host_control_policy")
def test_create_policy_profile(random_vm_control_policy,
                               random_host_control_policy,
                               random_policy_profile_name):
    global profile
    profile = explorer.PolicyProfile(
        random_policy_profile_name,
        policies=[random_vm_control_policy, random_host_control_policy]
    )
    profile.create()
    flash.assert_no_errors()
    assert profile.exists


@pytest.mark.requires("test_create_policy_profile")
def test_modify_policy_profile():
    global profile
    with update(profile):
        profile.notes = "Modified!"
    flash.assert_no_errors()
    sel.force_navigate("policy_profile", context={"policy_profile_name": profile.description})
    assert sel.text(profile.form.notes).strip() == "Modified!"


@pytest.mark.requires("test_create_policy_profile")
def test_delete_policy_profile():
    global profile
    profile.delete()
    flash.assert_no_errors()
    assert not profile.exists


@pytest.mark.requires("test_create_vm_control_policy")
def test_modify_vm_control_policy(random_vm_control_policy):
    with update(random_vm_control_policy):
        random_vm_control_policy.notes = "Modified!"
    flash.assert_no_errors()
    sel.force_navigate("vm_control_policy",
        context={"policy_name": random_vm_control_policy.description})
    assert sel.text(random_vm_control_policy.form.notes).strip() == "Modified!"


@pytest.mark.requires("test_create_vm_control_policy")
def test_delete_vm_control_policy(random_vm_control_policy):
    random_vm_control_policy.delete()
    flash.assert_no_errors()
    assert not random_vm_control_policy.exists


@pytest.mark.requires("test_create_host_control_policy")
def test_modify_host_control_policy(random_host_control_policy):
    with update(random_host_control_policy):
        random_host_control_policy.notes = "Modified!"
    flash.assert_no_errors()
    sel.force_navigate("host_control_policy",
        context={"policy_name": random_host_control_policy.description})
    assert sel.text(random_host_control_policy.form.notes).strip() == "Modified!"


@pytest.mark.requires("test_create_host_control_policy")
def test_delete_host_control_policy(random_host_control_policy):
    random_host_control_policy.delete()
    flash.assert_no_errors()
    assert not random_host_control_policy.exists


@pytest.mark.requires("test_create_action")
def test_modify_action(random_action):
    new_name = randomness.generate_random_string()
    with update(random_action):
        random_action.description = new_name
    flash.assert_no_errors()
    sel.force_navigate("control_explorer_action_edit",
        context={"action_name": random_action.description})
    assert sel.get_attribute(random_action.form.description, "value").strip() == new_name


@pytest.mark.requires("test_create_action")
def test_delete_action(random_action):
    random_action.delete()
    flash.assert_no_errors()
    assert not random_action.exists


@pytest.mark.requires("test_create_vm_condition")
def test_modify_vm_condition(random_vm_condition):
    with update(random_vm_condition):
        random_vm_condition.notes = "Modified!"
    flash.assert_no_errors()
    sel.force_navigate("vm_condition",
        context={"condition_name": random_vm_condition.description})
    assert sel.text(random_vm_condition.form.notes).strip() == "Modified!"


@pytest.mark.parametrize(("expression", "verify"), VM_EXPRESSIONS_TO_TEST)
@pytest.mark.requires("test_create_vm_condition")
def test_modify_vm_condition_expression(random_vm_condition, expression, verify):
    with update(random_vm_condition):
        random_vm_condition.expression = expression
    flash.assert_no_errors()
    if verify is not None:
        sel.force_navigate("vm_condition_edit",
            context={"condition_name": random_vm_condition.description})
        if not random_vm_condition.is_editing_expression:
            sel.click(random_vm_condition.buttons.edit_expression)
        assert expression_editor.get_expression_as_text() == verify


@pytest.mark.requires("test_create_vm_condition")
def test_delete_vm_condition(random_vm_condition):
    random_vm_condition.delete()
    flash.assert_no_errors()
    assert not random_vm_condition.exists


@pytest.mark.requires("test_create_host_condition")
def test_modify_host_condition(random_host_condition):
    with update(random_host_condition):
        random_host_condition.notes = "Modified!"
    flash.assert_no_errors()
    sel.force_navigate("host_condition",
        context={"condition_name": random_host_condition.description})
    assert sel.text(random_host_condition.form.notes).strip() == "Modified!"


@pytest.mark.requires("test_create_host_condition")
def test_delete_host_condition(random_host_condition):
    random_host_condition.delete()
    flash.assert_no_errors()
    assert not random_host_condition.exists


def test_create_alert(random_alert):
    random_alert.create()
    flash.assert_no_errors()
    assert random_alert.exists


@pytest.mark.requires("test_create_alert")
def test_update_alert(random_alert):
    with update(random_alert):
        random_alert.notification_frequency = "2 Hours"
    flash.assert_no_errors()
    sel.force_navigate("control_explorer_alert_edit",
        context={"alert_name": random_alert.description})
    assert sel.text(
        random_alert.form.notification_frequency.first_selected_option
    ).strip() == "2 Hours"


@pytest.mark.requires("test_create_alert")
def test_delete_alert(random_alert):
    random_alert.delete()
    flash.assert_no_errors()
    assert not random_alert.exists
