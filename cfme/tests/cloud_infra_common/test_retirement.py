# -*- coding: utf-8 -*-
import datetime
import pytest

from cfme import test_requirements
from cfme.common.provider import CloudInfraProvider
from cfme.common.vm import VM
from utils import testgen
from utils.generators import random_vm_name
from utils.log import logger
from utils.providers import ProviderFilter
from utils.timeutil import parsetime
from utils.wait import wait_for


pytest_generate_tests = testgen.generate(
    gen_func=testgen.providers,
    filters=[ProviderFilter(classes=[CloudInfraProvider], required_flags=['provision', 'retire'])],
    scope='module')


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(2),
    pytest.mark.long_running
]


@pytest.yield_fixture(scope="function")
def vm(small_template, provider):
    vm_obj = VM.factory(random_vm_name('retire'), provider, template_name=small_template)
    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    yield vm_obj

    try:
        if provider.mgmt.does_vm_exist(vm_obj.name):
            provider.mgmt.delete_vm(vm_obj.name)
    except Exception:
        logger.warning('Failed to delete vm from provider: {}'.format(vm_obj.name))


@pytest.yield_fixture(scope="function")
def existing_vm(provider):
    """ Fixture will be using for set\unset retirement date for existing vm instead of
    creation a new one
    """
    all_vms = provider.mgmt.list_vm()
    need_to_create_vm = True
    for virtual_machine in all_vms:
        if provider.mgmt.is_vm_running(virtual_machine):
            vm_obj = VM.factory(virtual_machine, provider)
            need_to_create_vm = False
            break
    if need_to_create_vm:
        machine_name = random_vm_name('retire')
        vm_obj = VM.factory(machine_name, provider)
        vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")

    yield vm_obj

    try:
        if need_to_create_vm and provider.mgmt.does_vm_exist(vm_obj.name):
            provider.mgmt.delete_vm(vm_obj.name)
    except Exception:
        logger.warning('Failed to delete vm from provider: {}'.format(vm_obj.name))


def verify_retirement(vm):
    # wait for the info block showing a date as retired date
    wait_for(lambda: vm.is_retired, delay=15, num_sec=10 * 60,
             message="Wait until VM {} will be retired".format(vm.name))

    assert vm.summary.power_management.power_state.text_value in {'off', 'suspended', 'unknown'}

    # make sure retirement date is today
    retirement_date = vm.retirement_date
    today = parsetime.now().to_american_date_only()
    assert retirement_date == today


@test_requirements.retirement
def test_retirement_now(vm):
    """Tests on-demand retirement of an instance/vm
    """
    vm.retire()
    verify_retirement(vm)


@test_requirements.retirement
def test_set_retirement_date(vm):
    """Tests retirement by setting a date
    """
    vm.set_retirement_date(datetime.datetime.now(), warn="1 Week before retirement")
    verify_retirement(vm)


@test_requirements.retirement
def test_unset_retirement_date(existing_vm):
    """Tests cancelling a scheduled retirement by removing the set date
    """
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    existing_vm.set_retirement_date(tomorrow)
    existing_vm.set_retirement_date(None)
    assert existing_vm.get_detail(properties=["Lifecycle", "Retirement Date"]) == "Never"
