# -*- coding: utf-8 -*-
"""This module contains tests that test the universally applicable canned methods in Automate."""
from datetime import date
from datetime import timedelta

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import InfraVmSummaryView
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
            logger.warn('Failed deleting VM from provider: %s', vm_name)
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
