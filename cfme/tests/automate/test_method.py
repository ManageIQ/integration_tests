# -*- coding: utf-8 -*-
from textwrap import dedent

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.klass import ClassDetailsView
from cfme.automate.simulation import simulate
from cfme.rest.gen_data import users as _users
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import ViaUI
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import FailPatternMatchError
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
    view.flash.assert_message(f'Automate Method "{method.name}" was added')
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
    with appliance.context.use(ViaREST):
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
@pytest.mark.meta(blockers=[BZ(1718495, forced_streams=['5.10'])], automates=[1718495, 1523379])
def test_embedded_method_selection(klass):
    """
    Bugzilla:
        1718495
        1523379

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
    """
    path = ("Datastore", "ManageIQ (Locked)", "System", "CommonMethods", "Utils", "log_object")
    view = navigate_to(klass.methods, "Add")
    view.fill({'location': "Inline", "embedded_method": path})
    assert view.embedded_method_table.read()[0]['Path'] == f"/{'/'.join(path[2:])}"


@pytest.mark.tier(1)
def test_automate_state_method(klass):
    """
    You can pass methods as states compared to the old method of passing
    instances which had to be located in different classes. You use the
    METHOD:: prefix

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        tags: automate
        startsin: 5.6
        testSteps:
            1. Create an automate class that has one state.
            2. Create a method in the class, make the method output
               something recognizable in the logs
            3. Create an instance inside the class, and as a Value for the
               state use: METHOD::method_name where method_name is the name
               of the method you created
            4. Run a simulation, use Request / Call_Instance to call your
               state machine instance
        expectedResults:
            1. Class created
            2. Method created
            3. Instance created
            4. The method got called, detectable by grepping logs
    """
    state = fauxfactory.gen_alpha()

    klass.schema.add_fields({'name': state, 'type': 'State'})

    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script="""\n$evm.log(:info, "Hello from state method")"""
    )

    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={state: {"value": f"METHOD::{method.name}"}}
    )

    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[".*Hello from state method.*"],
    )
    result.start_monitoring()

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
    assert result.validate()


@pytest.mark.parametrize(
    ("notify_level", "log_level"),
    [(":info", "info"), (":warning", "warning"), (":error", "error"), (":success", "success")],
    ids=["info", "warning", "error", "success"],
)
def test_method_for_log_and_notify(request, klass, notify_level, log_level):
    """
    PR:
        https://github.com/ManageIQ/manageiq-content/pull/423
        https://github.com/ManageIQ/manageiq-content/pull/362

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        startsin: 5.9
        casecomponent: Automate
        testSteps:
            1. Create a new Automate Method
            2. In the Automate Method screen embed ManageIQ/System/CommonMethods/Utils/log_object
               you can pick this method from the UI tree picker
            3. In your method add a line akin to
               ManageIQ::Automate::System::CommonMethods::Utils::LogObject.log_and_notify
               (:info, "Hello Testing Log & Notify", $evm.root['vm'], $evm)
            4. Check the logs and In your UI session you should see a notification
    """
    schema_name = fauxfactory.gen_alpha()
    # Adding schema for executing method
    klass.schema.add_fields({'name': schema_name, 'type': 'Method', 'data_type': 'String'})
    request.addfinalizer(lambda: klass.schema.delete_field(schema_name))

    # Adding automate method with embedded method
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        embedded_method=("Datastore", "ManageIQ (Locked)", "System", "CommonMethods", "Utils",
                         "log_object"),
        script='''
               \nManageIQ::Automate::System::CommonMethods::Utils::LogObject.log_ar_objects()
               \nManageIQ::Automate::System::CommonMethods::Utils::LogObject.current()
               \nManageIQ::Automate::System::CommonMethods::Utils::LogObject.log_and_notify({},
                              "Hello Testing Log & Notify", $evm.root['vm'], $evm)
               '''.format(notify_level)
    )
    request.addfinalizer(method.delete_if_exists)

    # Adding instance to call automate method
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={schema_name: {'value': method.name}}
    )
    request.addfinalizer(instance.delete_if_exists)

    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[
            ".*Validating Notification type: automate_user_{}.*".format(log_level),
            ".*Calling Create Notification type: automate_user_{}.*".format(log_level),
            ".*Hello Testing Log & Notify.*"
        ],
        failure_patterns=[".*ERROR.*"]
    )
    result.start_monitoring()

    # Executing automate method using simulation
    simulate(
        appliance=klass.appliance,
        message="create",
        request="Call_Instance",
        execute_methods=True,
        attributes_values={
            "namespace": klass.namespace.name,
            "class": klass.name,
            "instance": instance.name,
        }
    )
    if log_level == "error":
        with pytest.raises(FailPatternMatchError,
                           match="Pattern '.*ERROR.*': Expected failure pattern found in log."):
            result.validate(wait="60s")
    else:
        result.validate(wait="60s")


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1698184, forced_streams=['5.10'])], automates=[1698184])
def test_null_coalescing_fields(request, klass):
    """
    Bugzilla:
        1698184

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Automate
        tags: automate
        testSteps:
            1.  Create a Ruby method or Ansible playbook method with Input Parameters.
            2.  Use Data Type null coalescing
            3.  Make the default value something like this : ${#var3} || ${#var2} || ${#var1}
        expectedResults:
            1.
            2.
            3. Normal null coalescing behavior
    """
    var1, var2, var3, var4 = [fauxfactory.gen_alpha() for _ in range(4)]

    klass.schema.add_fields(
        *[
            {
                "name": var,
                "type": var_type,
                "data_type": "String",
                "default_value": value,
            }
            for var, value, var_type in [
                [var1, "fred", "Attribute"],
                [var2, "george", "Attribute"],
                [var3, " ", "Attribute"],
                [var4, "", "Method"],
            ]
        ]
    )
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location="inline",
        script=dedent(
            """
            $evm.log(:info, "Hello world")
            """
        ),
        inputs={
            "arg1": {
                "data_type": "null coalescing",
                "default_value": "".join(('${#', var1, '} ||${#', var2, '} ||${#', var3, '}'))
            },
            "arg2": {
                "data_type": "null coalescing",
                "default_value": "".join(('${#', var2, '} ||${#', var1, '} ||${#', var3, '}'))
            },
        },
    )
    request.addfinalizer(method.delete_if_exists)

    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={var4: {"value": method.name}}
    )
    request.addfinalizer(instance.delete_if_exists)

    log = LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[r'.*\[{\"arg1\"=>\"fred\", \"arg2\"=>\"george\"}\].*'],
    )
    log.start_monitoring()

    # Executing automate method using simulation
    simulate(
        appliance=instance.klass.appliance,
        message="create",
        request="Call_Instance",
        execute_methods=True,
        attributes_values={
            "namespace": instance.klass.namespace.name,
            "class": instance.klass.name,
            "instance": instance.name,
        },
    )

    assert log.validate()


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1411424])
def test_automate_user_has_groups(request, appliance, custom_instance):
    """
    This method should work:  groups = $evm.vmdb(:user).first.miq_groups
    $evm.log(:info, "Displaying the user"s groups: #{groups.inspect}")

    Bugzilla:
        1411424

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        tags: automate
        startsin: 5.8
    """
    user, user_data = _users(request, appliance)

    script = dedent(
        f"""
        group = $evm.vmdb(:user).find_by_name("{user[0].name}").miq_groups
        $evm.log(:info, "Displaying the user's groups: #{{group.inspect}}")
        """
    )
    instance = custom_instance(ruby_code=script)

    with LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[f'.*{user_data[0]["group"]["description"]}.*'],
    ).waiting(timeout=120):

        # Executing automate method using simulation
        simulate(
            appliance=instance.klass.appliance,
            message="create",
            request="Call_Instance",
            execute_methods=True,
            attributes_values={
                "namespace": instance.klass.namespace.name,
                "class": instance.klass.name,
                "instance": instance.name,
            },
        )


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1592140])
def test_copy_with_embedded_method(request, appliance, klass):
    """
    When copying a method within the automate model the copied method
    does not have the Embedded Methods that are a part of the source method

    Bugzilla:
        1592140

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/2h
        testSteps:
            1. Create a method in the automate model that has one or more Embedded Methods added
            2. Copy the method to a new domain
    """
    path = ("Datastore", "ManageIQ (Locked)", "System", "CommonMethods", "Utils", "log_object")
    embedded_method_path = f"/{'/'.join(path[2:])}"
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location="inline",
        script='$evm.log(:info, ":P")',
        embedded_method=path,
    )
    request.addfinalizer(method.delete_if_exists)
    view = navigate_to(method, "Details")
    assert view.embedded_method_table.read()[0]["Path"] == embedded_method_path

    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alpha(), description=fauxfactory.gen_alpha(), enabled=True
    )
    request.addfinalizer(domain.delete_if_exists)
    method.copy_to(domain.name)

    copied_method = (
        domain.namespaces.instantiate(klass.namespace.name)
        .classes.instantiate(klass.name)
        .methods.instantiate(method.name)
    )
    view = navigate_to(copied_method, "Details")
    assert view.embedded_method_table.read()[0]["Path"] == embedded_method_path
