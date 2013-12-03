# -*- encoding: utf-8 -*-

import random
import pytest

""" Unit tests for Control tab coverage (https://github.com/RedHatQE/cfme_tests/pull/206/)

To fully test, I recommend running this unittest on a machine which already has some policies
imported. E.g. machine set up for event testing.

@author: Milan Falešník <mfalesni@redhat.com>
"""


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
def test_conditions_accordion(control_explorer_pg, random_string):
    """ Check adding and editing conditions

    Marked as nondestructive even that it creates new stuff, but it deletes it again.
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

    new.description = random_string
    new.notes = random_string
    view = new.add()

    # Touch the basic elements
    view.scope
    view.expression
    view.notes
    view.refresh()
    # Try some editing
    edit = view.edit()
    edit.notes = random_string + random_string  # This must enable reset
    assert edit.reset(), "Could not reset the changes!"
    edit.notes = random_string + random_string  # This must enable save
    view = edit.save()
    assert "was saved" in view.flash.message, "Could not save the condition"
    assert view.notes == random_string + random_string, "notes aren't equal"
    # And delete it
    conditions = view.delete()
    assert "successful" in conditions.flash.message


@pytest.mark.nondestructive
def test_events_accordion(control_explorer_pg):
    """ Pick a random event and check its elements

    Can take a while. If not found, ends in 10 tries
    """
    events = control_explorer_pg.click_on_events_accordion()
    finished = False
    counter = 0
    while not finished and counter < 10:
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


@pytest.mark.nondestructive
def test_policies_tab(control_explorer_pg, random_string):
    """ Check adding and editing policies

    Marked as nondestructive even that it creates new stuff, but it deletes it again.
    """
    p = control_explorer_pg.click_on_policies_accordion()
    new = p.add_new_host_control_policy()
    p = new.cancel()
    new = p.add_new_host_control_policy()
    new.deactivate()
    new.activate()
    assert new.is_active, "Policy is not set to be active"
    new.notes = "I Can Has Cheezburger?"
    new.description = random_string
    assert new.description == random_string, "Could not set the input#description"
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
    p = view.delete_policy()
