# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest


@pytest.fixture(scope="module", params=["vm"])
def retirement_policies_setup_data(request, cfme_data):
    '''Returns data for retirement policies'''
    param = request.param
    return cfme_data.data["retirement_policy_setup"][param]


@pytest.fixture
def setup_retirement_policies(
        control_explorer_pg,
        retirement_policies_setup_data):
    '''Sets up retire policy for vms'''
    policies_pg = control_explorer_pg.click_on_policies_accordion()
    new_policy_pg = policies_pg._new_policy('Vm Control Policies')
    new_policy_pg.description_input.send_keys("Vm Retirement")
    policy_view_pg = new_policy_pg.add()
    # Add a new policy event (Vm Retired)
    edit_policy_pg = policy_view_pg.edit_policy_event_assignments()
    edit_policy_pg.vm_retired_checkbox.click()
    vm_policy_view_pg = edit_policy_pg.save()
    # Edit the actions this event (Raise Automation Event, Retire, Delete from Disk)
    policy_event_view_pg = vm_policy_view_pg.go_to_event("VM Retired")
    policy_event_actions_edit_pg = policy_event_view_pg.edit_actions()
    policy_event_actions_edit_pg.enable_action_true("Raise Automation Event")
    policy_event_actions_edit_pg.enable_action_true("Retire Virtual Machine")
    policy_event_actions_edit_pg.enable_action_true("Delete VM from Disk")
    policy_event_actions_edit_pg.save()
    policy_event_actions_edit_pg._wait_for_results_refresh()
    # Add a new policy profile
    policy_profiles_pg = control_explorer_pg.click_on_policy_profiles_accordion()
    new_policy_profile_pg = policy_profiles_pg.new_policy_profile("Vm Control Policy Profile")
    new_policy_profile_pg.description_input.send_keys("Vm  Retirement Profile")
    new_policy_profile_pg.enable_policy_true("VM and Instance Control: Vm Retirement")
    new_policy_profile_pg.add()
