# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest


@pytest.fixture
def setup_retirement_policies(
        control_explorer_pg):
    '''Sets up retire policy for vms'''
    policies_pg = control_explorer_pg.click_on_policies_accordion()
    new_policy_pg = policies_pg.add_new_vm_control_policy()
    new_policy_pg.description_input.send_keys("Vm Retirement")
    policy_view_pg = new_policy_pg.add()
    if "has already been taken" in policy_view_pg.flash.message:
        policy_view_pg = new_policy_pg.cancel()
    # Add a new policy event (Vm Retired)
    policy_view_pg = policy_view_pg.select_vm_control_policy("Vm Retirement")
    policy_view_pg.set_assigned_events({"VM Retired": True})
    # Edit the actions this event (Raise Automation Event, Retire, Delete from Disk)
    policy_event_view_pg = policy_view_pg.go_to_event("VM Retired")
    policy_event_actions_edit_pg = policy_event_view_pg.edit_actions()
    policy_event_actions_edit_pg.enable_action_true("Raise Automation Event")
    policy_event_actions_edit_pg.enable_action_true("Retire Virtual Machine")
    policy_event_actions_edit_pg.enable_action_true("Delete VM from Disk")
    if policy_event_actions_edit_pg.can_save:
        policy_event_view_pg = policy_event_actions_edit_pg.save()
    else:
        # Already exists
        policy_event_view_pg = policy_event_actions_edit_pg.cancel()
    # Add a new policy profile
    policy_profiles_pg = policy_event_view_pg.click_on_policy_profiles_accordion()
    new_policy_profile_pg = policy_profiles_pg.new_policy_profile()
    new_policy_profile_pg.description_input.send_keys("Vm Retirement Profile")
    new_policy_profile_pg.enable_policy("VM and Instance Control: Vm Retirement")
    if new_policy_profile_pg.can_add:
        new_policy_profile_pg.add()
