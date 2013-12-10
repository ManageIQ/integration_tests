# -*- encoding: utf-8 -*-
""" Unit tests for Control tab coverage (https://github.com/RedHatQE/cfme_tests/pull/206/)

To fully test, I recommend running this unittest on a machine which already has some policies
imported. E.g. machine set up for event testing.

@author: Milan Falešník <mfalesni@redhat.com>
"""

import random
import pytest
from utils import randomness


# To keep the names to be able to pair them together
@pytest.fixture(scope="module")
def condition_name():
    return randomness.generate_random_string()


@pytest.fixture(scope="module")
def policy_name():
    return randomness.generate_random_string()


@pytest.mark.nondestructive
def test_click_the_accordion(control_explorer_pg):
    """ Basic test whether accordion works

    """
    page = control_explorer_pg
    page = page.click_on_policy_profiles_accordion()
    page = page.click_on_policies_accordion()
    page = page.click_on_events_accordion()
    page = page.click_on_conditions_accordion()
    page = page.click_on_actions_accordion()
    page = page.click_on_alert_profiles_accordion()
    page = page.click_on_alerts_accordion()


@pytest.mark.nondestructive
def test_expression_editor(control_explorer_pg, random_string):
    """ This test is supposed to test every possible combination of the expression field.

    """
    conditions = control_explorer_pg.click_on_conditions_accordion()
    page = conditions.add_new_host_condition()
    page.edit_expression()
    page.delete_all_expressions()
    page.select_first_expression()
    page.new_fill_expression_field(field="Host.Datastores : Last Analysis Time",
                                   value=(2013, 12, 10, 16, 15))
    page.discard_expression()
    page.new_fill_expression_field(field="Host.vSwitches : Date Created", value=(2013, 12, 10))
    page.discard_expression()
    page.new_fill_expression_field(field="Host.vSwitches : Date Created", value="2 Days Ago")
    page.discard_expression()
    page.new_fill_expression_field(field="Host.vSwitches : Ports", value="1234 5678 9012 3456")
    page.discard_expression()
    page.new_fill_expression_field(field="Host : Authentication Status", chosen_key="IS NULL")
    page.discard_expression()
    page.new_fill_expression_field(field="Host : Authentication Status",
                                   chosen_key="REGULAR EXPRESSION MATCHES",
                                   value="asdbcd")
    page.discard_expression()
    page.new_fill_expression_field(field="Host : Authentication Status",
                                   chosen_key="RUBY",
                                   value="puts \"hello\"")
    page.discard_expression()
    page.new_fill_expression_field(field="Host.VMs : Disk 5 Size", value="10", suffix="GB")
    page.discard_expression()


def test_conditions_accordion(control_explorer_pg, condition_name):
    """ Check adding and editing conditions

    """
    conditions = control_explorer_pg.click_on_conditions_accordion()
    new = conditions.add_new_host_condition()
    new.edit_expression()
    new.edit_scope()
    new.edit_expression()
    new.delete_all_expressions()
    new.select_first_expression()
    new.fill_expression_field("Host : Connection State", "=", "rubbish")
    new.commit_expression()

    new.select_expression_by_text("Connection State")
    new.AND_expression()
    new.fill_expression_count("Host.Files", "=", "1")
    new.commit_expression()

    new.select_expression_by_text("Host.Files")
    new.NOT_expression()
    new.select_expression_by_text("Host.Files")
    new.AND_expression()
    new.fill_expression_tag("Host.My Company Tags : Cost Center", "Cost Center 001")
    new.commit_expression()

    new.description = condition_name
    new.notes = condition_name
    view = new.add()

    # Touch the basic elements
    view.scope
    view.expression
    view.notes
    view.refresh()
    # Try some editing
    edit = view.edit()
    edit.notes = condition_name + condition_name  # This must enable reset
    assert edit.reset(), "Could not reset the changes!"
    edit.notes = condition_name + condition_name  # This must enable save
    view = edit.save()
    assert "was saved" in view.flash.message, "Could not save the condition"
    assert view.notes == condition_name + condition_name, "notes aren't equal"


@pytest.mark.nondestructive
def test_events_accordion(control_explorer_pg):
    """ Pick a random event and check its elements

    Can take a while. If not found, ends in 10 tries
    """
    events = control_explorer_pg.click_on_events_accordion()
    finished = False
    counter = 0
    while not finished and counter < 5:
        random_event = random.choice(events.events)[1]
        event = events.get_event(random_event)
        # Touch the elements
        event.event_group
        policies = event.assigned_policies
        if policies:
            for policy in policies:
                policy.text
            finished = True
        event.refresh()
        counter += 1


@pytest.mark.nondestructive
def test_log_tab(control_log_pg):
    """ Just basic test to touch the elements

    """
    control_log_pg.download     # Touch the download button
    control_log_pg.log          # Try to take the text from the textarea


def test_policies_accordion(control_explorer_pg, policy_name):
    """ Check adding and editing policies

    """
    p = control_explorer_pg.click_on_policies_accordion()
    new = p.add_new_host_control_policy()
    p = new.cancel()
    new = p.add_new_host_control_policy()
    new.deactivate()
    new.activate()
    assert new.is_active, "Policy is not set to be active"
    new.notes = "I Can Has Cheezburger?"
    new.description = policy_name
    assert new.description == policy_name, "Could not set the input#description"
    # Some expression editing
    new.delete_all_expressions()
    new.select_first_expression()
    new.fill_expression_field("Host : Hostname", "INCLUDES", "cheezburger")
    new.commit_expression()

    new.select_expression_by_text("cheezburger")
    new.NOT_expression()
    new.select_expression_by_text("cheezburger")
    new.OR_expression()
    new.fill_expression_tag("Host.My Company Tags : Cost Center", "Cost Center 001")
    new.commit_expression()
    view = new.add()
    # Uncomment when the glitch with button disappear
    #assert "was added" in view.flash.message, "Could not add a new policy"
    assert "I Can Has Cheezburger?" in view.notes, "Incorrect save"
    assert "cheezburger" in view.scope, "Failed to check the scope against the original"
    edit = view.edit_basic()
    edit.notes = "lol"
    assert edit.reset(), "Could not reset the form"
    edit.delete_all_expressions()
    edit.select_first_expression()
    edit.fill_expression_field("Host : Hostname", "INCLUDES", "hamburger")
    edit.commit_expression()
    view = edit.save()
    assert "was saved" in view.flash.message, "Error when saving the policy"


@pytest.mark.requires_test("test_policies_accordion")
@pytest.mark.requires_test("test_conditions_accordion")
def test_assign_condition_to_policy(control_explorer_pg, policy_name, condition_name):
    p = control_explorer_pg.click_on_policies_accordion()
    policy = p.select_host_control_policy(policy_name)
    conditions = policy.edit_policy_condition_assignments()
    assert conditions.use_condition(condition_name), "Could not select and move the condition"
    policy = conditions.save()
    assert "was saved" in policy.flash.message


def test_cleanup(control_explorer_pg, policy_name, condition_name):
    p = control_explorer_pg.click_on_policies_accordion()
    p = p.delete_host_control_policy(policy_name)
    c = p.click_on_conditions_accordion()
    c = c.delete_host_condition(condition_name)
    assert "Delete successful" in c.flash.message
