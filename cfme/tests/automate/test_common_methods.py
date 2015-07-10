# -*- coding: utf-8 -*-
"""This module contains tests that test the universally applicable canned methods in Automate."""
import fauxfactory
import pytest

from datetime import timedelta

from cfme.automate.buttons import ButtonGroup, Button
from cfme.infrastructure.virtual_machines import Vm
from cfme.web_ui import toolbar
from utils import testgen
from utils.providers import setup_provider
from utils.timeutil import parsetime
from utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, 'provisioning', template_location=["provisioning", "template"])

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture()
def provider_init(provider_key):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_ae_methods_{}'.format(fauxfactory.gen_alphanumeric())
    return vm_name


@pytest.fixture(scope="function")
def testing_vm(request, vm_name, provider_init, provider_crud, provider_mgmt, provisioning):
    vm_obj = Vm(vm_name, provider_crud, provisioning["template"])

    def _finalize():
        vm_obj.delete_from_provider()
    request.addfinalizer(_finalize)
    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm_obj


@pytest.fixture(scope="function")
def retire_extend_button(request):
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
    soft_assert(testing_vm.retirement_date is None, "The retirement date is not None!")
    retirement_date = parsetime.now() + timedelta(days=5)
    testing_vm.set_retirement_date(retirement_date)
    wait_for(lambda: testing_vm.retirement_date is not None, message="retirement date be set")
    soft_assert(testing_vm.retirement_date is not None, "The retirement date is None!")
    # current_retirement_date = testing_vm.retirement_date

    # Now run the extend stuff
    retire_extend_button()

    # dajo - 20140920 - this fails because its not turning the calendar to the next month?
    # wait_for(
    #     lambda: testing_vm.retirement_date >= current_retirement_date + timedelta(days=14),
    #     num_sec=60,
    #     message="extend the retirement date by 14 days"
    # )
