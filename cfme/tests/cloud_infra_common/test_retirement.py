# -*- coding: utf-8 -*-
"""This module tests retirement of cloud and infrastructure vm."""
import fauxfactory
import pytest
import datetime

from cfme.cloud.instance import EC2Instance, OpenStackInstance
from cfme.infrastructure.virtual_machines import Vm
from functools import partial
from utils import testgen
from utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers')

]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.all_providers(
        metafunc, 'small_template', template_location=["small_template"])

    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="module")
def vm_crud(provider, small_template):
    """To simplify the logic in the test, this fixture picks the correct class."""
    # TODO: Use the factory after the provider unification is done
    if provider.type == "ec2":
        cls = EC2Instance
    elif provider.type == "openstack":
        cls = OpenStackInstance
    else:
        cls = Vm
    return cls(
        'test_retire_prov_{}'.format(fauxfactory.gen_alpha(length=8).lower()),
        provider, template_name=small_template)


@pytest.fixture(scope="function")
def vm(request, setup_provider, vm_crud, provider):
    request.addfinalizer(lambda: provider.mgmt.delete_vm(vm_crud.name)
        if provider.mgmt.does_vm_exist(vm_crud.name) else None)
    vm_crud.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm_crud


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
