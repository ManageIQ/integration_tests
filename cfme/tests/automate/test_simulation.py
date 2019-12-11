import fauxfactory
import pytest

from . import user_list_hash_data
from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.base.ui import AutomateSimulationView
from cfme.control.explorer.actions import ActionDetailsView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator

pytestmark = [test_requirements.automate, pytest.mark.tier(2)]


@pytest.mark.meta(automates=[1719322])
def test_object_attributes(appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/16h

    Bugzilla:
        1719322
    """
    view = navigate_to(appliance.server, "AutomateSimulation")
    # Collecting all the options available for object attribute type
    for object_type in view.target_type.all_options[1:]:
        view.reset_button.click()
        if BZ(1719322, forced_streams=['5.10', '5.11']).blocks and object_type.text in [
            "Group",
            "EVM Group",
            "Tenant",
        ]:
            continue
        else:
            # Selecting object attribute type
            view.target_type.select_by_visible_text(object_type.text)
            # Checking whether dependent objects(object attribute selection) are loaded or not
            assert len(view.target_object.all_options) > 0


@pytest.fixture(scope='function')
def copy_class(domain):
    # Take the 'Request' class and copy it to custom domain.
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="System"
    ).classes.instantiate(name="Request").copy_to(domain.name)
    klass = domain.namespaces.instantiate(name="System").classes.instantiate(name="Request")
    return klass


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1335669])
def test_assert_failed_substitution(copy_class):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        caseposneg: negative
        tags: automate

    Bugzilla:
        1335669
    """
    # Adding instance and invalid value for assertion field - 'guard'
    instance = copy_class.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={'guard': {'value': "${/#this_value_does_not_exist}"}}
    )

    # Executing automate instance using simulation
    with pytest.raises(AssertionError,
                       match="Automation Error: Attribute this_value_does_not_exist not found"):
        simulate(
            appliance=copy_class.appliance,
            attributes_values={
                "namespace": copy_class.namespace.name,
                "class": copy_class.name,
                "instance": instance.name,
            },
            message="create",
            request="Call_Instance",
            execute_methods=True,
        )


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1445089])
def test_automate_simulation_result_has_hash_data(custom_instance):
    """
    The UI should display the result objects if the Simulation Result has
    hash data.

    Bugzilla:
        1445089

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate
        testSteps:
            1. Create a Instance under /System/Request called ListUser, update it so that it points
               to a ListUser Method
            2. Create ListUser Method under /System/Request, paste the Attached Method
            3. Run Simulation
        expectedResults:
            1.
            2.
            3. The UI should display the result objects
    """
    instance = custom_instance(ruby_code=user_list_hash_data)

    # Executing automate method
    with LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=['.*User List.*:id=>1, :name=>"Fred".*']).waiting(timeout=120):

        simulate(
            appliance=instance.appliance,
            attributes_values={
                "namespace": instance.klass.namespace.name,
                "class": instance.klass.name,
                "instance": instance.name,
            },
            message="create",
            request="Call_Instance",
            execute_methods=True,
        )
    view = instance.create_view(AutomateSimulationView)
    assert (
        view.result_tree.click_path(
            f"ManageIQ/SYSTEM / PROCESS / {instance.klass.name}",
            f"ManageIQ/System / {instance.klass.name} / Call_Instance",
            f"{instance.domain.name}/System / {instance.klass.name} / {instance.name}",
            "values",
            "Hash",
            "Key",
        ).text
        == "Key"
    )


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1630800, forced_streams=["5.11"])], automates=[1630800])
def test_simulation_copy_button(appliance):
    """
    Bugzilla:
        1630800

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Go to Automation > Automate > Simulation
            2. Fill in any required fields to enable submit button and click on 'Submit'
            4. Change any field - for example 'Object Attribute'
            5. Select Copy button
        expectedResults:
            1. Copy button should be disabled
            2. Copy button should be enabled
            3.
            4.
            5. Copy button should be disabled until form is submitted
    """
    view = navigate_to(appliance.server, 'AutomateSimulation')
    assert not view.copy.is_enabled
    view.fill({
        'instance': "Request",
        'message': "Hello",
        'request': "InspectMe",
        'execute_methods': True,
        'target_type': "EVM User",
        'target_object': "Administrator",
    })
    view.submit_button.click()
    assert view.copy.is_enabled
    view.target_type.select_by_visible_text("Provider")
    assert not view.copy.is_enabled


@pytest.mark.meta(automates=[1753523], blockers=[BZ(1753523, forced_streams=['5.10'])])
def test_attribute_value_message(custom_instance):
    """
    Bugzilla:
        1753523

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup:
            1. Create domain, namespace, class and instance pointing to method
        testSteps:
            1. Navigate to automate > automation > simulation page
            2. Fill values for attribute/value pairs of namespace, class, instance and add message
               attribute with any value and click on submit.
            3. See automation.log
        expectedResults:
            1.
            2.
            3. Custom message attribute should be considered with instance in logs
    """
    instance = custom_instance(ruby_code=None)
    msg = fauxfactory.gen_alphanumeric()

    # Executing automate method
    with LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[f".*{instance.name}#{msg}.*"]).waiting(timeout=120):
        simulate(
            appliance=instance.appliance,
            attributes_values={
                "namespace": instance.klass.namespace.name,
                "class": instance.klass.name,
                "instance": instance.name,
                "message": msg
            },
            message="create",
            request="call_instance_with_message",
            execute_methods=True,
        )


@pytest.mark.meta(automates=[1672007])
def test_action_invoke_custom_automation(request, appliance):
    """
    Bugzilla:
        1672007

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Navigate to Control > explorer > actions
            2. Select 'add a new action' from configuration dropdown
            3. Add description and select 'Action Type' - Invoke custom automation
            4. Fill attribute value pairs and click on add
            5. Edit the created action and add new attribute value pair
            6. Remove that newly added attribute value pair before clicking on save and then click
               on save
        expectedResults:
            1.
            2.
            3.
            4.
            5. Save button should enabled
            6. Action should be saved successfully
    """
    attr_val = [
        {f"attribute_{num}": fauxfactory.gen_alpha() for num in range(1, 6)} for _ in range(2)
    ]

    automation_action = appliance.collections.actions.create(
        fauxfactory.gen_alphanumeric(),
        "Invoke a Custom Automation",
        dict(
            message=fauxfactory.gen_alpha(),
            request=fauxfactory.gen_alpha(),
            attribute_value_pair=attr_val[0]
        )
    )
    request.addfinalizer(automation_action.delete_if_exists)

    view = navigate_to(automation_action, "Edit")
    view.attribute_value_pair.fill(attr_val[1])
    assert view.save_button.is_enabled
    view.attribute_value_pair.clear()
    view.save_button.click()
    view = automation_action.create_view(ActionDetailsView, wait="10s")
    view.flash.assert_success_message(f'Action "{automation_action.description}" was saved')
