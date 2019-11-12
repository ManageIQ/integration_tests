from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


def simulate(
    appliance,
    instance=None,
    message=None,
    request=None,
    target_type=None,
    target_object=None,
    execute_methods=True,
    attributes_values=None,
    pre_clear=True,
):
    """Runs the simulation of specified Automate object.

    Args:
        appliance: Appliance object
        instance: Type of object from `/System/Process/` that will initiate the model
        message: Message
        request: Name of the instance where you like to point
        target_type: Type of item you want to run the simulation
        target_object: Name of target object from target type
        execute_methods: True if you want to perform the model and not just simulate it else False
        attributes_values: attribute value pair
        pre_clear: clear before simulation
    """

    view = navigate_to(appliance.server, 'AutomateSimulation')
    if pre_clear:
        view.avp.clear()
        view.fill({
            'instance': 'Request',
            'message': 'create',
            'request': '',
            'target_type': '<None>',
            'execute_methods': True, })
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
    wait_for(
        lambda: view.flash.is_displayed,
        delay=10,
        timeout=120
    )
    view.flash.assert_no_error()
    view.flash.assert_message('Automation Simulation has been run')
    # TODO: After fixing the tree
    # return view.result_tree.read_contents()
