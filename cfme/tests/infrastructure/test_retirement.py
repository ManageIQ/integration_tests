# -*- coding: utf-8 -*-
import datetime
import fauxfactory
import pytest
from functools import partial

from cfme.common.vm import VM
from utils import testgen
from utils.wait import wait_for


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


@pytest.fixture(scope="function")
def vm(request, setup_provider, provider, provisioning):
    vm_name = 'test_retire_prov_%s' % fauxfactory.gen_alphanumeric()
    myvm = VM.factory(vm_name, provider, template_name=provisioning['template'])
    request.addfinalizer(myvm.delete_from_provider)
    myvm.create_on_provider(find_in_cfme=True, allow_skip="default")
    return myvm


def verify_retirement(vm):
    today = datetime.date.today()
    get_date = partial(vm.get_detail, ["Lifecycle", "Retirement Date"])
    get_state = partial(vm.get_detail, ["Power Management", "Power State"])

    # wait for the info block showing a date as retired date
    def retirement_date_present():
        return get_date() != "Never"

    wait_for(retirement_date_present, delay=30, num_sec=600, message="retirement_date_present")

    # wait for the power state to go to 'off'
    wait_for(lambda: get_state() == "off", delay=30, num_sec=360)

    # make sure retirement date is today
    assert datetime.datetime.strptime(get_date(), "%m/%d/%y").date() == today


def test_retirement_now(vm):
    """Tests retirement

    Metadata:
        test_flag: retire, provision
    """
    vm.retire()
    verify_retirement(vm)


def test_set_retirement_date(vm):
    """Tests retirement

    Metadata:
        test_flag: retire, provision
    """
    vm.set_retirement_date(datetime.date.today())
    verify_retirement(vm)


def test_unset_retirement_date(vm):
    """Tests retirement

    Metadata:
        test_flag: retire, provision
    """
    try:
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        vm.set_retirement_date(tomorrow)
        vm.set_retirement_date(None)
        assert vm.get_detail(["Lifecycle", "Retirement Date"]) == "Never"
    finally:
        vm.retire()
