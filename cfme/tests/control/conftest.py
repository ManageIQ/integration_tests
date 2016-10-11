# -*- coding: utf-8 -*-

import pytest

from cfme.common.vm import VM
from fixtures.pytest_store import store
from functools import partial
from utils.log import logger
from utils.virtual_machines import deploy_template
from utils.wait import wait_for, TimedOutError
from utils.pretty import Pretty


class VMWrapper(Pretty):
    """This class binds a provider_mgmt object with VM name. Useful for on/off operation"""
    __slots__ = ("_prov", "_vm", "api", "crud")
    pretty_attrs = ['_vm', '_prov']

    def __init__(self, provider, vm_name, api):
        self._prov = provider
        self._vm = vm_name
        self.api = api
        self.crud = VM.factory(vm_name, self._prov)

    @property
    def name(self):
        return self._vm

    @property
    def provider(self):
        return self._prov.mgmt

    def __getattr__(self, key):
        """Creates partial functions proxying to mgmt_system.<function_name>(vm_name)"""
        func = getattr(self._prov.mgmt, key)
        return partial(func, self._vm)


def get_vm_object(vm_name):
    """Looks up the CFME database for the VM.

    Args:
        vm_name: VM name

    Returns:
        If found, :py:class:`utils.api.Entity`
        If not, `None`
    """
    try:
        return pytest.store.current_appliance.rest_api.collections.vms.find_by(name=vm_name)[0]
    except IndexError:
        return None


@pytest.fixture(scope="module")
def local_setup_provider(request, setup_provider_modscope, provider):
    if provider.type == 'virtualcenter':
        store.current_appliance.install_vddk(reboot=True)
        store.current_appliance.wait_for_web_ui()
        try:
            pytest.sel.refresh()
        except AttributeError:
            # In case no browser is started
            pass


@pytest.fixture(scope="module")
def vm(request, provider, local_setup_provider, small_template_modscope, vm_name):
    if provider.type == "rhevm":
        kwargs = {"cluster": provider.data["default_cluster"]}
    elif provider.type == "virtualcenter":
        kwargs = {}
    elif provider.type == "openstack":
        kwargs = {}
        if 'small_template_flavour' in provider.data:
            kwargs = {"flavour_name": provider.data.get('small_template_flavour')}
    elif provider.type == "scvmm":
        kwargs = {
            "host_group": provider.data.get("provisioning", {}).get("host_group", "All Hosts")}
    else:
        kwargs = {}

    try:
        deploy_template(
            provider.key,
            vm_name,
            template_name=small_template_modscope,
            allow_skip="default",
            power_on=True,
            **kwargs
        )
    except TimedOutError as e:
        logger.exception(e)
        try:
            provider.mgmt.delete_vm(vm_name)
        except TimedOutError:
            logger.warning("Could not delete VM %s!", vm_name)
        finally:
            # If this happened, we should skip all tests from this provider in this module
            pytest.skip("{} is quite likely overloaded! Check its status!\n{}: {}".format(
                provider.key, type(e).__name__, str(e)))

    @request.addfinalizer
    def _finalize():
        """if getting REST object failed, we would not get the VM deleted! So explicit teardown."""
        logger.info("Shutting down VM with name %s", vm_name)
        if provider.mgmt.is_vm_suspended(vm_name):
            logger.info("Powering up VM %s to shut it down correctly.", vm_name)
            provider.mgmt.start_vm(vm_name)
        if provider.mgmt.is_vm_running(vm_name):
            logger.info("Powering off VM %s", vm_name)
            provider.mgmt.stop_vm(vm_name)
        if provider.mgmt.does_vm_exist(vm_name):
            logger.info("Deleting VM %s in %s", vm_name, provider.mgmt.__class__.__name__)
            provider.mgmt.delete_vm(vm_name)

    # Make it appear in the provider
    provider.refresh_provider_relationships()

    # Get the REST API object
    api = wait_for(
        lambda: get_vm_object(vm_name),
        message="VM object {} appears in CFME".format(vm_name),
        fail_condition=None,
        num_sec=600,
        delay=15,
    )[0]

    return VMWrapper(provider, vm_name, api)


@pytest.fixture(scope="module")
def vm_crud(vm_name, provider):
    return VM.factory(vm_name, provider)


@pytest.fixture(scope="function")
def vm_on(vm, vm_crud):
    """ Ensures that the VM is on when the control goes to the test."""
    vm.wait_vm_steady()
    if not vm.is_vm_running():
        vm.start_vm()
        vm.wait_vm_running()
    # Make sure the state is consistent
    vm_crud.refresh_relationships(from_details=True)
    vm_crud.wait_for_vm_state_change(desired_state=vm_crud.STATE_ON, from_details=True)
    return vm


@pytest.fixture(scope="function")
def vm_off(vm, vm_crud):
    """ Ensures that the VM is off when the control goes to the test."""
    vm.wait_vm_steady()
    if vm.is_vm_suspended():
        vm.start_vm()
        vm.wait_vm_running()
    if not vm.is_vm_stopped():
        vm.stop_vm()
        vm.wait_vm_stopped()
    # Make sure the state is consistent
    vm_crud.refresh_relationships(from_details=True)
    vm_crud.wait_for_vm_state_change(desired_state=vm_crud.STATE_OFF, from_details=True)
    return vm


@pytest.fixture(scope="function")
def vm_crud_refresh(vm_crud, provider):
    """Refreshes the VM if that is needed for the provider."""
    if provider.type in {"ec2"}:
        return lambda: vm_crud.refresh_relationships(from_details=True)
    else:
        return lambda: None