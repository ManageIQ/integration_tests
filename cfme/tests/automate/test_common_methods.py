# -*- coding: utf-8 -*-
"""This module contains tests that test the universally applicable canned methods in Automate."""
from datetime import date
from datetime import timedelta
from textwrap import dedent

import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVmSummaryView
from cfme.provisioning import do_vm_provisioning
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Dropdown

pytestmark = [
    test_requirements.automate,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.provider([InfraProvider], required_fields=[
        ['provisioning', 'template'],
        ['provisioning', 'host'],
        ['provisioning', 'datastore']
    ], scope="module")
]


@pytest.fixture(scope="function")
def testing_vm(request, setup_provider, provider, provisioning):
    collection = provider.appliance.provider_based_collection(provider)
    vm_name = random_vm_name('ae-methods')
    vm_obj = collection.instantiate(vm_name, provider, provisioning["template"])

    def _finalize():
        try:
            vm_obj.cleanup_on_provider()
        except Exception:
            logger.warning('Failed deleting VM from provider: %s', vm_name)
    request.addfinalizer(_finalize)
    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm_obj


def generate_retirement_date(delta=None):
    gen_date = date.today()
    if delta:
        gen_date += timedelta(days=delta)
    return gen_date


@pytest.mark.rhv3
@pytest.mark.tier(3)
def test_vm_retire_extend(appliance, request, testing_vm, soft_assert):
    """ Tests extending a retirement using an AE method.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/3h
        setup:
            1. A running VM on any provider.
        testSteps:
            1. It creates a button pointing to ``Request/vm_retire_extend`` instance. The button
               should live in the VM and Instance button group.
            2. Then it sets a retirement date for the VM
            3. Then it waits until the retirement date is set
            4. Then it clicks the button that was created and it waits for the retirement date to
               extend.

    Bugzilla:
        1627758
    """
    num_days = 5
    soft_assert(testing_vm.retirement_date == 'Never', "The retirement date is not 'Never'!")
    retirement_date = generate_retirement_date(delta=num_days)
    testing_vm.set_retirement_date(retirement_date)
    wait_for(lambda: testing_vm.retirement_date != 'Never', message="retirement date set")
    set_date = testing_vm.retirement_date
    vm_retire_date_fmt = testing_vm.RETIRE_DATE_FMT

    soft_assert(set_date == retirement_date.strftime(vm_retire_date_fmt),
                "The retirement date '{}' did not match expected date '{}'"
                .format(set_date, retirement_date.strftime(vm_retire_date_fmt)))

    # Create the vm_retire_extend button and click on it
    grp_name = "grp_{}".format(fauxfactory.gen_alphanumeric())
    grp = appliance.collections.button_groups.create(
        text=grp_name,
        hover=grp_name,
        type=appliance.collections.button_groups.VM_INSTANCE
    )
    request.addfinalizer(lambda: grp.delete_if_exists())
    btn_name = "btn_{}".format(fauxfactory.gen_alphanumeric())
    button = grp.buttons.create(
        text=btn_name,
        hover=btn_name,
        system="Request",
        request="vm_retire_extend"
    )
    request.addfinalizer(lambda: button.delete_if_exists())

    navigate_to(testing_vm, 'Details')

    class TestDropdownView(InfraVmSummaryView):
        group = Dropdown(grp.text)

    view = appliance.browser.create_view(TestDropdownView)
    view.group.item_select(button.text)

    # CFME automate vm_retire_extend method defaults to extending the date by 14 days
    extend_duration_days = 14
    extended_retirement_date = retirement_date + timedelta(days=extend_duration_days)

    # Check that the WebUI updates with the correct date
    wait_for(
        lambda: testing_vm.retirement_date >= extended_retirement_date.strftime(vm_retire_date_fmt),
        num_sec=60,
        message="Check for extension of the VM retirement date by {} days".format(
            extend_duration_days)
    )


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1720432])
def test_miq_password_decrypt(klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/3h

    Bugzilla:
        1720432
    """
    # Ruby script for decrypting password
    script = (
        'require "manageiq-password"\n'
        'root_password = MiqPassword.encrypt("abc")\n'
        '$evm.log("info", "Root Password is #{root_password}")\n'
        'root_password_decrypted = MiqPassword.decrypt(root_password)\n'
        '$evm.log("info", "Decrypted password is #{root_password_decrypted}")'
    )

    # Adding schema for executing method
    klass.schema.add_fields({'name': 'execute', 'type': 'Method', 'data_type': 'String'})

    # Adding automate method
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
        fields={'execute': {'value': method.name}}
    )

    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=[".*Decrypted password is abc.*"],
    )
    result.start_monitoring()

    # Executing method via simulation to check decrypted password
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


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1700524])
@pytest.mark.ignore_stream("5.10")
def test_service_retirement_from_automate_method(request, generic_catalog_item, custom_instance):
    """
    Bugzilla:
        1700524

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        startsin: 5.11
        casecomponent: Automate
        testSteps:
            1. Create service catalog item and order
            2. Create a writeable domain and copy ManageIQ/System/Request to this domain
            3. Create retire_automation_service instance and set meth5 to retire_automation_service.
            4. Create retire_automation_service method with sample code given below:
               > service = $evm.root['service']
               > $evm.log(:info, "create_retire_request for  service #{service}")
               > request = $evm.execute(:create_retire_request, service)
               > $evm.log(:info, "Create request for create_retire_request #{request}")
            5. Execute this method using simulation
        expectedResults:
            1. Service provision request should be provisioned successfully
            2.
            3.
            4.
            5. Service should be retired successfully
    """
    # Ordering catalog item and deleting request once service has been reached to 'Finished' state
    service_request = generic_catalog_item.appliance.rest_api.collections.service_templates.get(
        name=generic_catalog_item.name
    ).action.order()
    request.addfinalizer(lambda: service_request.action.delete())
    wait_for(lambda: service_request.request_state == "finished", fail_func=service_request.reload,
             timeout=180, delay=10)

    # Ruby code to execute create_retire_request
    script = dedent(
        """
        service = $evm.root['service']
        $evm.log(:info, 'create_retire_request for service #{service}')
        request = $evm.execute(:create_retire_request, service)
        $evm.log(:info, 'Create request for create_retire_request #{request}')
        """
    )
    instance = custom_instance(ruby_code=script)
    with LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=['.*Create request for create_retire_request.*']).waiting(timeout=120):

        # Executing automate method
        simulate(
            appliance=generic_catalog_item.appliance,
            target_type="Service",
            target_object=f"{generic_catalog_item.name}",
            message="create",
            request=f"{instance.name}",
            execute_methods=True,
        )

    retire_request = generic_catalog_item.appliance.rest_api.collections.requests.get(
        description=f"Service Retire for: {generic_catalog_item.name}")
    wait_for(lambda: retire_request.request_state == "finished", fail_func=retire_request.reload,
             timeout=180, delay=10)


@pytest.fixture
def set_root_tenant_quota(request, appliance):
    field, value = request.param
    root_tenant = appliance.collections.tenants.get_root_tenant()
    root_tenant.set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    root_tenant.set_quota(**{'{}_cb'.format(field): False})


@pytest.mark.tier(3)
@pytest.mark.usefixtures("setup_provider")
@pytest.mark.meta(automates=[1334318])
@pytest.mark.provider([VMwareProvider], override=True)
@pytest.mark.parametrize(
    ['set_root_tenant_quota'],
    [
        [('memory', '1000')],
    ],
    indirect=['set_root_tenant_quota'],
    ids=['memory']
)
def test_automate_quota_units(request, set_root_tenant_quota, provisioning, provider, appliance):
    """
    Bugzilla:
        1334318

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/4h
        tags: automate
    """
    vm_name = random_vm_name(context='quota')

    prov_data = {
        "catalog": {'vm_name': vm_name},
        "environment": {'automatic_placement': True},
        "network": {'vlan': partial_match(provisioning['vlan'])},
        'hardware': {'memory': '1024'},
    }

    @request.addfinalizer
    def _finalize():
        collection = appliance.provider_based_collection(provider)
        vm_obj = collection.instantiate(vm_name, provider, provisioning["template"])
        try:
            vm_obj.cleanup_on_provider()
        except Exception:
            logger.warning('Failed deleting VM from provider: %s', vm_name)

    with LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[f'.*Getting Tenant Quota Values for:.*.memory=>1073741824000.*'],
    ).waiting(timeout=120):
        # Provisioning VM via lifecycle
        do_vm_provisioning(appliance, template_name=provisioning["template"], provider=provider,
                           vm_name=vm_name, provisioning_data=prov_data, wait=False, request=None)

        # nav to requests page to check quota validation
        request_description = f'Provision from [{provisioning["template"]}] to [{vm_name}]'
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method='ui')
        assert provision_request.is_succeeded(
            method="ui"
        ), f"Provisioning failed: {provision_request.row.last_message.text}"
