# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.klass import ClassDetailsView
from cfme.automate.simulation import simulate
from cfme.rest.gen_data import service_templates as _service_templates
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.automate, pytest.mark.tier(2)]


@pytest.fixture(scope='function')
def original_class(domain):
    # Take the 'Request' class and copy it for own purpose.
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="System"
    ).classes.instantiate(name="Request").copy_to(domain.name)
    klass = domain.namespaces.instantiate(name="System").classes.instantiate(name="Request")
    return klass


@pytest.mark.sauce
def test_method_crud(klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/16h
        tags: automate
    """
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='$evm.log(:info, ":P")',
    )
    view = method.create_view(ClassDetailsView)
    view.flash.assert_message('Automate Method "{}" was added'.format(method.name))
    assert method.exists
    origname = method.name
    with update(method):
        method.name = fauxfactory.gen_alphanumeric(8)
        method.script = "bar"
    assert method.exists
    with update(method):
        method.name = origname
    assert method.exists
    method.delete()
    assert not method.exists


@pytest.mark.sauce
def test_automate_method_inputs_crud(appliance, klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/8h
        caseimportance: critical
        tags: automate
    """
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='blah',
        inputs={
            'foo': {'data_type': 'string'},
            'bar': {'data_type': 'integer', 'default_value': '42'}}
    )
    assert method.exists
    view = navigate_to(method, 'Details')
    assert view.inputs.is_displayed
    assert view.inputs.read() == {
        'foo': {'Data Type': 'string', 'Default Value': ''},
        'bar': {'Data Type': 'integer', 'Default Value': '42'},
    }
    with update(method):
        method.inputs = {'different': {'default_value': 'value'}}
    view = navigate_to(method, 'Details')
    assert view.inputs.is_displayed
    assert view.inputs.read() == {
        'different': {'Data Type': 'string', 'Default Value': 'value'},
    }
    with update(method):
        method.inputs = {}
    view = navigate_to(method, 'Details')
    assert not view.inputs.is_displayed
    method.delete()


def test_duplicate_method_disallowed(klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseposneg: negative
        initialEstimate: 1/10h
        caseimportance: critical
        tags: automate
    """
    name = fauxfactory.gen_alpha()
    klass.methods.create(
        name=name,
        location='inline',
        script='$evm.log(:info, ":P")',
    )
    with pytest.raises(Exception, match="Name has already been taken"):
        klass.methods.create(
            name=name,
            location='inline',
            script='$evm.log(:info, ":P")',
        )


@pytest.mark.tier(1)
def test_automate_simulate_retry(klass, domain, namespace, original_class):
    """Automate simulation now supports simulating the state machines.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.6
        casecomponent: Automate
        tags: automate
        title: Test automate simulate retry
        setup:
            1. Create a state machine that contains a couple of states
        testSteps:
            1. Create an Automate model that has a State Machine that can end in a retry
            2. Run a simulation to test the Automate Model from Step 1
            3. When the Automation ends in a retry, we should be able to resubmit the request
            4. Use automate simulation UI to call the state machine (Call_Instance)
        expectedResults:
            1.
            2.
            3.
            4. A Retry button should appear.

    Bugzilla:
        1299579
    """
    # Adding schema for running 'RETRY' method
    klass.schema.add_fields({'name': 'RUN', 'type': 'Method', 'data_type': 'String'})

    # Adding 'RETRY' method
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='''root = $evm.root \n
                  if root['ae_state_retries'] && root['ae_state_retries'] > 2 \n
                  \t \t root['ae_result'] = 'ok'\n else \t \t root['ae_result'] = 'retry' \n end''',
    )

    # Adding 'RETRY_METHOD' instance to call 'RETRY' method
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={'RUN': {'value': method.name}}
    )

    # Creating new class in same domain/namespace
    new_class = namespace.collections.classes.create(name=fauxfactory.gen_alphanumeric())

    # Creating schema of new class with 'TYPE' - 'State'
    new_class.schema.add_fields({'name': 'STATE1', 'type': 'State', 'data_type': 'String'})

    # Adding new instance - 'TEST_RETRY' to new class which calls instance - 'RETRY_METHOD'
    new_instance = new_class.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={
            "STATE1": {
                "value": "/{domain}/{namespace}/{klass}/{instance}".format(
                    domain=domain.name,
                    namespace=namespace.name,
                    klass=klass.name,
                    instance=instance.name,
                )
            }
        },
    )

    # Creating instance 'MY_TEST' under original class which uses relationship - 'rel1' of schema to
    # call new_instance - 'TEST_RETRY'
    original_instance = original_class.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        fields={
            "rel1": {
                "value": "/{domain}/{namespace}/{klass}/{instance}".format(
                    domain=domain.name,
                    namespace=namespace.name,
                    klass=new_class.name,
                    instance=new_instance.name,
                )
            }
        },
    )

    # Navigating to 'AutomateSimulation' view to check whether retry button is not available before
    # executing automate method
    view = navigate_to(klass.appliance.server, 'AutomateSimulation')
    assert not view.retry_button.is_displayed

    # Executing automate method - 'RETRY' using simulation
    simulate(
        appliance=klass.appliance,
        instance="Request",
        message="create",
        request=original_instance.name,
        execute_methods=True
    )

    # Checking whether 'Retry' button is displayed
    assert view.retry_button.is_displayed


@pytest.fixture(scope='module')
def service_catalog(request, dialog, catalog):
    """This fixture is used to create generic service catalog item"""
    cat_item = _service_templates(
        request, dialog.appliance, service_dialog=dialog, service_catalog=catalog, num=1
    )[0]
    yield cat_item
    cat_item.action.delete()


@pytest.mark.tier(1)
def test_task_id_for_method_automation_log(service_catalog, appliance):
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/30h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Automate
        tags: automate
        setup:
            1. Add existing or new automate method to newly created domain or create generic service
        testSteps:
            1. Run that instance using simulation or order service catalog item
            2. See automation log
        expectedResults:
            1.
            2. Task id should be included in automation log for method logs.

    Bugzilla:
        1592428
    """
    service_catalog.action.order()

    # Need to wait for some seconds to get automation logs
    wait_for(lambda: False, silent_failure=True, timeout=20)
    result = appliance.ssh_client.run_command(
        "grep 'Q-task_id' /var/www/miq/vmdb/log/automation.log"
    )
    assert result.success
