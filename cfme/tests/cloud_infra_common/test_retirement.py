# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import fauxfactory
import pytest

from cfme.common.vm import VM
from utils import testgen
from utils.wait import wait_for
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers'),
    pytest.mark.tier(2)
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
    # add condition because of differ behaviour between 5.5 and 5.6
    if current_version() < "5.6":
        wait_for(lambda: vm.exists is False, delay=30, num_sec=360,
                 message="Wait for VM {} removed from provider".format(vm.name))
    else:
        today = datetime.date.today()

        # wait for the info block showing a date as retired date
        @pytest.wait_for(delay=30, timeout='5m')
        def retirement_date_present():
            vm.summary.reload()
            return vm.summary.lifecycle.retirement_date.text_value.lower() != 'never'

        # wait for the state to change
        @pytest.wait_for(delay=15, timeout='6m')
        def wait_for_retired():
            vm.summary.reload()
            return vm.summary.lifecycle.retirement_state.text_value.lower() == 'retired'

        assert vm.summary.power_management.power_state.text_value in {'off', 'suspended', 'unknown'}

        # make sure retirement date is today
        retirement_date = vm.summary.lifecycle.retirement_date.text_value.lower()
        assert datetime.datetime.strptime(retirement_date, "%m/%d/%y").date() == today


@pytest.mark.meta(blockers=[1337697])
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
