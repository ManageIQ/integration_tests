# -*- coding: utf-8 -*-
import datetime
import fauxfactory
import pytest
from functools import partial

from cfme.common.vm import VM
from utils import testgen
from utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers')
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.all_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="function")
def vm(request, provider, setup_provider, small_template):
    vm_obj = VM.factory(
        'test_retire_prov_{}'.format(fauxfactory.gen_alpha(length=8).lower()),
        provider, template_name=small_template)

    @request.addfinalizer
    def _delete_vm():
        if provider.mgmt.does_vm_exist(vm_obj.name):
            provider.mgmt.delete_vm(vm_obj.name)
    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm_obj


def verify_retirement(vm):
    today = datetime.date.today()
    get_date = partial(vm.get_detail, ["Lifecycle", "Retirement Date"])
    get_state = partial(vm.get_detail, ["Power Management", "Power State"])

    # wait for the info block showing a date as retired date
    def retirement_date_present():
        return get_date() != "Never"

    wait_for(retirement_date_present, delay=30, num_sec=600, message="retirement_date_present")

    # wait for the power state to go to 'off'
    wait_for(lambda: get_state() in {'off', 'suspended'}, delay=30, num_sec=360)

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
