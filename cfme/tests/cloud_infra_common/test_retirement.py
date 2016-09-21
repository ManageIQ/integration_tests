# -*- coding: utf-8 -*-
import datetime
import fauxfactory
import pytest

from cfme.common.vm import VM
from utils import testgen, providers
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


@pytest.fixture(scope="function")
def existing_vm(request):
    """ Fixture will be using for set\unset retirement date for existing vm instead of
    creation a new one
    """
    list_of_existing_providers = providers.existing_providers()
    if list_of_existing_providers:
        test_provider = providers.get_crud(list_of_existing_providers[0])
    else:
        test_provider = providers.setup_a_provider()
    all_vms = test_provider.mgmt.list_vm()
    need_to_create_vm = True
    for virtual_machine in all_vms:
        if test_provider.mgmt.is_vm_running(virtual_machine):
            need_vm = VM.factory(virtual_machine, test_provider)
            need_to_create_vm = False
            break
    if need_to_create_vm:
        machine_name = 'test_retire_prov_{}'.format(fauxfactory.gen_alpha(length=8).lower())
        need_vm = VM.factory(machine_name, test_provider)
        need_vm.create_on_provider(find_in_cfme=True, allow_skip="default")

    @request.addfinalizer
    def _delete_vm():
        if need_to_create_vm:
            test_provider.mgmt.delete_vm(need_vm.name)
    return need_vm


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


def test_set_unset_retirement_date_tomorrow(existing_vm):
    """Tests retirement

    Metadata:
        test_flag: retire, provision
    """
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    existing_vm.set_retirement_date(tomorrow)
    existing_vm.set_retirement_date(None)
    assert existing_vm.get_detail(["Lifecycle", "Retirement Date"]) == "Never"
