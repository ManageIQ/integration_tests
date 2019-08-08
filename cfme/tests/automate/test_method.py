# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.klass import ClassDetailsView
from cfme.automate.simulation import simulate
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import ViaUI
from cfme.utils.log_validator import LogValidator
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
    # TODO(ghubale@redhat.com): Update this test case for other types of automate methods like
    #  builtin, expression, uri, playbook, Ansible Tower Job Template and Ansible Tower Workflow
    #  Template
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='$evm.log(:info, ":P")',
    )
    view = method.create_view(ClassDetailsView)
    if not False:
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


@pytest.mark.tier(1)
def test_task_id_for_method_automation_log(request, generic_catalog_item):
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
    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=[".*Q-task_id.*"]
    )
    result.start_monitoring()
    service_request = generic_catalog_item.appliance.rest_api.collections.service_templates.get(
        name=generic_catalog_item.name
    ).action.order()
    request.addfinalizer(service_request.action.delete)

    # Need to wait until automation logs with 'Q-task_id' are generated, which happens after the
    # service_request becomes active.
    wait_for(lambda: service_request.request_state == "active", fail_func=service_request.reload,
             timeout=60, delay=3)
    assert result.validate(wait="60s")


@pytest.mark.meta(server_roles="+notifier")
def test_send_email_method(smtp_test, klass):
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/20h
        startsin: 5.10
        casecomponent: Automate

    Bugzilla:
        1688500
        1702304
    """
    mail_to = fauxfactory.gen_email()
    mail_cc = fauxfactory.gen_email()
    mail_bcc = fauxfactory.gen_email()
    schema_field = fauxfactory.gen_alphanumeric()

    # Ruby code to send emails
    script = (
        'to = "{mail_to}"\n'
        'subject = "Hello"\n'
        'body = "Hi"\n'
        'bcc = "{mail_bcc}"\n'
        'cc = "{mail_cc}"\n'
        'content_type = "message"\n'
        'from = "cfadmin@cfserver.com"\n'
        "$evm.execute(:send_email, to, from, subject, body, {{:bcc => bcc, :cc => cc,"
        ":content_type => content_type}})"
    )
    script = script.format(mail_cc=mail_cc, mail_bcc=mail_bcc, mail_to=mail_to)

    # Adding schema for executing method - send_email which helps to send emails
    klass.schema.add_fields({'name': schema_field, 'type': 'Method', 'data_type': 'String'})

    # Adding method - send_email for sending mails
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script=script)

    # Adding instance to call automate method - send_email
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={schema_field: {'value': method.name}}
    )

    result = LogValidator(
        "/var/www/miq/vmdb/log/evm.log",
        matched_patterns=[
            '.*:to=>"{mail_to}".*.*:cc=>"{mail_cc}".*.*:bcc=>"{mail_bcc}".*'.format(
                mail_to=mail_to, mail_cc=mail_cc, mail_bcc=mail_bcc
            )
        ],
    )
    result.start_monitoring()

    # Executing automate method - send_email using simulation
    simulate(
        appliance=klass.appliance,
        attributes_values={
            "namespace": klass.namespace.name,
            "class": klass.name,
            "instance": instance.name,
        },
        message="create",
        request="Call_Instance",
        execute_methods=True,
    )
    assert result.validate(wait="60s")

    # TODO(GH-8820): This issue should be fixed to check mails sent to person in 'cc' and 'bcc'
    # Check whether the mail sent via automate method really arrives
    wait_for(lambda: len(smtp_test.get_emails(to_address=mail_to)) > 0, num_sec=60, delay=10)


@pytest.fixture(scope="module")
def generic_object_definition(appliance):
    # Creating generic object using REST
    with appliance.context.use(ViaREST):
        definition = appliance.collections.generic_object_definitions.create(
            name="LoadBalancer_{}".format(fauxfactory.gen_numeric_string(3)),
            description="LoadBalancer",
            attributes={"location": "string"},
            associations={"vms": "Vm", "services": "Service"}
        )
        yield definition
        definition.delete_if_exists()


@pytest.fixture
def go_service_request(generic_catalog_item):
    # Creating generic service
    service_request = generic_catalog_item.appliance.rest_api.collections.service_templates.get(
        name=generic_catalog_item.name
    ).action.order()
    yield
    service_request.action.delete()


@pytest.mark.tier(1)
def test_automate_generic_object_service_associations(appliance, klass, go_service_request,
                                                      generic_object_definition):
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/10h
        caseimportance: medium
        startsin: 5.7
        casecomponent: Automate

    Bugzilla:
        1410920
    """
    schema_field = fauxfactory.gen_alphanumeric()
    # Ruby code
    script = 'go_class = $evm.vmdb(:generic_object_definition).find_by(:name => "{name}")\n'.format(
        name=generic_object_definition.name
    )
    script = script + (
        'load_balancer = go_class.create_object(:name => "Test Load Balancer", :location => '
        '"Mahwah")\n'
        '$evm.log("info", "XYZ go object: #{load_balancer.inspect}")\n'
        'service = $evm.vmdb(:service).first\n'
        'load_balancer.services = [service]\n'
        'content_type = "message"\n'
        'load_balancer.save!\n'
        '$evm.log("info", "XYZ load balancer got service: #{load_balancer.services.first.inspect}")'
        '\nexit MIQ_OK'
    )
    with appliance.context.use(ViaUI):
        # Adding schema for executing method
        klass.schema.add_fields({'name': schema_field, 'type': 'Method', 'data_type': 'String'})

        # Adding method
        method = klass.methods.create(
            name=fauxfactory.gen_alphanumeric(),
            display_name=fauxfactory.gen_alphanumeric(),
            location='inline',
            script=script)

        # Adding instance to call automate method
        instance = klass.instances.create(
            name=fauxfactory.gen_alphanumeric(),
            display_name=fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            fields={schema_field: {'value': method.name}}
        )

        result = LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[
                r'.*XYZ go object: #<MiqAeServiceGenericObject.*',
                r'.*XYZ load balancer got service: #<MiqAeServiceService.*'
            ],
        )
        result.start_monitoring()

        # Executing automate method using simulation
        simulate(
            appliance=klass.appliance,
            attributes_values={
                "namespace": klass.namespace.name,
                "class": klass.name,
                "instance": instance.name,
            },
            message="create",
            request="Call_Instance",
            execute_methods=True,
        )
        assert result.validate(wait="60s")


@pytest.mark.tier(1)
def test_automate_service_quota_runs_only_once(appliance, generic_catalog_item):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        tags: automate

    Bugzilla:
        1317698
    """
    pattern = ".*Getting Tenant Quota Values for:.*"
    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[pattern]
    )
    result.start_monitoring()
    service_catalogs = ServiceCatalogs(
        appliance, catalog=generic_catalog_item.catalog, name=generic_catalog_item.name
    )
    provision_request = service_catalogs.order()
    provision_request.wait_for_request()
    assert result.matches[pattern] == 1


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1718495])
def test_embedded_method_selection():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        casecomponent: Automate
        testSteps:
            1. Create a new inline method in CloudForms Automate.
            2. Add an embedded method.
        expectedResults:
            1.
            2. Selected embedded method should be visible

    Bugzilla:
        1718495
    """
    pass
