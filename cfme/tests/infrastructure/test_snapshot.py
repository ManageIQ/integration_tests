# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.simulation import simulate
from cfme.common.vm import VM
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import Vm  # For Vm.Snapshot
from utils import testgen
from utils.conf import credentials
from utils.log import logger
from utils.path import data_path
from utils.ssh import SSHClient
from utils.wait import wait_for


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    test_requirements.snapshot
]


pytest_generate_tests = testgen.generate([InfraProvider], scope="module")


@pytest.fixture(scope="module")
def vm_name():
    return "test_snpsht_" + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def domain(request):
    dom = DomainCollection().create(name=fauxfactory.gen_alpha(), enabled=True)
    request.addfinalizer(dom.delete_if_exists)
    return dom


@pytest.fixture(scope="module")
def test_vm(setup_provider_modscope, provider, vm_name, request):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm = VM.factory(vm_name, provider, template_name=provider.data['full_template']['name'])

    if not provider.mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        request.addfinalizer(vm.delete_from_provider)
    return vm


def new_snapshot(test_vm, has_name=True):
    if has_name:
        new_snapshot = Vm.Snapshot(
            name="snpshot_" + fauxfactory.gen_alphanumeric(8),
            description="snapshot", memory=False, parent_vm=test_vm
        )
    else:
        new_snapshot = Vm.Snapshot(
            description="snapshot_" + fauxfactory.gen_alphanumeric(8),
            memory=False, parent_vm=test_vm
        )
    return new_snapshot


@pytest.mark.uncollectif(lambda provider:
    not provider.one_of(RHEVMProvider, VMwareProvider) or
    (provider.one_of(RHEVMProvider) and provider.version < 4))
def test_snapshot_crud(test_vm, provider):
    """Tests snapshot crud

    Metadata:
        test_flag: snapshot, provision
    """
    if provider.one_of(RHEVMProvider):
        snapshot = new_snapshot(test_vm, has_name=False)
    else:
        snapshot = new_snapshot(test_vm)
    snapshot.create()
    snapshot.delete()


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_delete_all_snapshots(test_vm, provider):
    """Tests snapshot removal

    Metadata:
        test_flag: snapshot, provision
    """
    snapshot1 = new_snapshot(test_vm)
    snapshot1.create()
    snapshot2 = new_snapshot(test_vm)
    snapshot2.create()
    snapshot2.delete_all()


@pytest.mark.uncollectif(lambda provider:
    not provider.one_of(RHEVMProvider, VMwareProvider) or
    (provider.one_of(RHEVMProvider) and provider.version < 4))
def test_verify_revert_snapshot(test_vm, provider, soft_assert, register_event, request):
    """Tests revert snapshot

    Metadata:
        test_flag: snapshot, provision
    """
    if provider.one_of(RHEVMProvider):
        snapshot1 = new_snapshot(test_vm, has_name=False)
    else:
        snapshot1 = new_snapshot(test_vm)

    ssh_kwargs = {
        'hostname': snapshot1.vm.provider.mgmt.get_ip_address(snapshot1.vm.name),
        'username': credentials[provider.data['full_template']['creds']]['username'],
        'password': credentials[provider.data['full_template']['creds']]['password']
    }

    ssh_client = SSHClient(**ssh_kwargs)
    # We need to wait for ssh to become available on the vm, it can take a while. Without
    # this wait, the ssh command would fail with 'port 22 not available' error.
    # Easiest way to solve this is just mask the exception with 'handle_exception = True'
    # and wait for successful completition of the ssh command.
    # The 'fail_func' ensures we close the connection that failed with exception.
    # Without this, the connection would hang there and wait_for would fail with timeout.
    wait_for(lambda: ssh_client.run_command('touch snapshot1.txt').rc == 0, num_sec=300,
             delay=20, handle_exception=True, fail_func=ssh_client.close())
    snapshot1.create()
    register_event(target_type='VmOrTemplate', target_name=test_vm.name,
                   event_type='vm_snapshot_complete')
    register_event(target_type='VmOrTemplate', target_name=test_vm.name,
                   event_type='vm_snapshot')
    ssh_client.run_command('touch snapshot2.txt')

    if provider.one_of(RHEVMProvider):
        snapshot2 = new_snapshot(test_vm, has_name=False)
    else:
        snapshot2 = new_snapshot(test_vm)
    snapshot2.create()

    if provider.one_of(RHEVMProvider):
        test_vm.power_control_from_cfme(option=test_vm.POWER_OFF, cancel=False)
        test_vm.wait_for_vm_state_change(
            desired_state=test_vm.STATE_OFF, timeout=900)

    snapshot1.revert_to()

    # Wait for the snapshot to become active
    logger.info('Waiting for vm %s to become active', snapshot1.name)
    wait_for(lambda: snapshot1.active, num_sec=300, delay=20, fail_func=sel.refresh)
    test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_OFF, timeout=720)
    test_vm.power_control_from_cfme(option=test_vm.POWER_ON, cancel=False)
    test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_ON, timeout=900)
    current_state = test_vm.find_quadicon().state
    soft_assert(current_state.startswith('currentstate-on'),
                "Quadicon state is {}".format(current_state))
    soft_assert(test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm not running")
    wait_for(lambda: ssh_client.run_command('test -e snapshot1.txt').rc == 0,
             num_sec=400, delay=20, handle_exception=True, fail_func=ssh_client.close())
    try:
        result = ssh_client.run_command('test -e snapshot1.txt')
        assert not result.rc
        result = ssh_client.run_command('test -e snapshot2.txt')
        assert result.rc
        logger.info('Revert to snapshot %s successful', snapshot1.name)
    except:
        logger.exception('Revert to snapshot %s Failed', snapshot1.name)
    ssh_client.close()


@pytest.mark.uncollectif(lambda provider: not provider.one_of(VMwareProvider))
def test_create_snapshot_via_ae(request, domain, test_vm):
    """This test checks whether the vm.create_snapshot works in AE.

    Prerequisities:
        * A VMware provider
        * A VM that has been discovered by CFME

    Steps:
        * Clone the Request class inside the System namespace into a new domain
        * Add a method named ``snapshot`` and insert the provided code there.
        * Add an instance named ``snapshot`` and set the methd from previous step
            as ``meth5``
        * Run the simulation of the method against the VM, preferably setting
            ``snap_name`` to something that can be checked
        * Wait until snapshot with such name appears.
    """
    # PREPARE
    file = data_path.join("ui").join("automate").join("test_create_snapshot_via_ae.rb")
    with file.open("r") as f:
        method_contents = f.read()
    miq_domain = DomainCollection().instantiate(name='ManageIQ')
    miq_class = miq_domain.namespaces.instantiate(name='System').classes.instantiate(name='Request')
    miq_class.copy_to(domain)
    request_cls = domain.namespaces.instantiate(name='System').classes.instantiate(name='Request')
    request.addfinalizer(request_cls.delete)
    method = request_cls.methods.create(name="snapshot", location='inline', script=method_contents)
    request.addfinalizer(method.delete)
    instance = request_cls.instances.create(
        name="snapshot",
        fields={
            "meth5": {
                'value': "snapshot"}})
    request.addfinalizer(instance.delete)

    # SIMULATE
    snap_name = fauxfactory.gen_alpha()
    snapshot = Vm.Snapshot(name=snap_name, parent_vm=test_vm)
    simulate(
        instance="Request",
        request="snapshot",
        target_type='VM and Instance',
        target_object=test_vm.name,
        execute_methods=True,
        attributes_values={"snap_name": snap_name})

    wait_for(lambda: snapshot.exists, timeout="2m", delay=10,
             fail_func=sel.refresh, handle_exception=True)

    # Clean up if it appeared
    snapshot.delete()
