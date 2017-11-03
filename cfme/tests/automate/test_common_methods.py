# -*- coding: utf-8 -*-
"""This module contains tests that test the universally applicable canned methods in Automate."""
import fauxfactory
import pytest

from datetime import timedelta, date

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.automate.buttons import ButtonGroup, Button
from cfme.common.vm import VM
from cfme.web_ui import toolbar
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from cfme.utils.version import pick


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
def vm_name():
    vm_name = 'test_ae_methods_{}'.format(fauxfactory.gen_alphanumeric())
    return vm_name


@pytest.fixture(scope="function")
def testing_vm(request, vm_name, setup_provider, provider, provisioning):
    vm_obj = VM.factory(vm_name, provider, provisioning["template"])

    def _finalize():
        try:
            vm_obj.delete_from_provider()
        except Exception:
            logger.warn('Failed deleting VM from provider: %s', vm_name)
    request.addfinalizer(_finalize)
    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm_obj


@pytest.fixture(scope="function")
def retire_extend_button(request):
    """
    Add an automate button that will extend the vm retirement date
    """
    grp_name = "grp_{}".format(fauxfactory.gen_alphanumeric())
    grp = ButtonGroup(
        text=grp_name,
        hover=grp_name,
        type=ButtonGroup.VM_INSTANCE
    )
    request.addfinalizer(lambda: grp.delete_if_exists())
    grp.create()
    btn_name = "btn_{}".format(fauxfactory.gen_alphanumeric())
    button = Button(
        group=grp,
        text=btn_name,
        hover=btn_name,
        system="Request",
        request="vm_retire_extend"
    )
    request.addfinalizer(lambda: button.delete_if_exists())
    button.create()

    return lambda: toolbar.select(grp.text, button.text)


def generate_retirement_date(delta=None):
    gen_date = date.today()
    if delta:
        gen_date += timedelta(days=delta)
    return gen_date


@pytest.mark.tier(3)
def test_vm_retire_extend(request, testing_vm, soft_assert, retire_extend_button):
    """ Tests extending a retirement using an AE method.

    Prerequisities:
        * A running VM on any provider.

    Steps:
        * It creates a button pointing to ``Request/vm_retire_extend`` instance. The button should
            live in the VM and Instance button group.
        * Then it sets a retirement date for the VM
        * Then it waits until the retirement date is set
        * Then it clicks the button that was created and it waits for the retirement date to extend.

    Metadata:
        test_flag: retire, provision
    """
    num_days = 5
    soft_assert(testing_vm.retirement_date == 'Never', "The retirement date is not 'Never'!")
    retirement_date = generate_retirement_date(delta=num_days)
    testing_vm.set_retirement_date(retirement_date)
    wait_for(lambda: testing_vm.retirement_date != 'Never', message="retirement date set")
    set_date = testing_vm.retirement_date
    if not BZ(1419150, forced_streams='5.6').blocks:
        soft_assert(set_date == retirement_date.strftime(pick(VM.RETIRE_DATE_FMT)),
                    "The retirement date '{}' did not match expected date '{}'"
                    .format(set_date, retirement_date.strftime(pick(VM.RETIRE_DATE_FMT))))

    # Create the vm_retire_extend button and click on it
    retire_extend_button()

    # CFME automate vm_retire_extend method defaults to extending the date by 14 days
    extend_duration_days = 14
    extended_retirement_date = retirement_date + timedelta(days=extend_duration_days)

    # Check that the WebUI updates with the correct date
    wait_for(
        lambda: testing_vm.retirement_date >= extended_retirement_date.strftime(
            pick(VM.RETIRE_DATE_FMT)),
        num_sec=60,
        message="Check for extension of the VM retirement date by {} days".format(
            extend_duration_days)
    )
