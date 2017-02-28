# -*- coding: utf-8 -*-
from utils.appliance import get_or_create_current_appliance
from utils.appliance.implementations.ui import navigate_to


def simulate(
        instance=None, message=None, request=None, target_type=None, target_object=None,
        execute_methods=None, attributes_values=None, appliance=None):
    """Runs the simulation of specified Automate object."""
    if not appliance:
        appliance = get_or_create_current_appliance()
    view = navigate_to(appliance.server, 'AutomateSimulation')
    view.fill({
        'instance': instance,
        'message': message,
        'request': request,
        'target_type': target_type,
        'target_object': target_object,
        'execute_methods': execute_methods,
        'avp': attributes_values,
    })
    view.submit_button.click()
    view.flash.assert_no_error()
    view.flash.assert_message('Automation Simulation has been run')
