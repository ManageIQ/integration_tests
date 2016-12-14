# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer import Domain, Namespace, Class, Instance, Method
from cfme.automate.simulation import simulate
from cfme.common.vm import VM
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm  # For Vm.Snapshot
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.conf import credentials
from utils.log import logger
from utils.path import data_path
from utils.ssh import SSHClient
from utils.wait import wait_for


pytestmark = [pytest.mark.long_running,
              pytest.mark.tier(2),
              test_requirements.snapshot]


pytest_generate_tests = testgen.generate([InfraProvider], scope="module")


@pytest.fixture(scope="module")
def vm_name():
    return "test_snpsht_" + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def domain(request):
    dom = Domain(fauxfactory.gen_alpha(), enabled=True)
    dom.create()
    request.addfinalizer(dom.delete)
    return dom


@pytest.fixture(scope="module")
def test_vm(setup_provider_modscope, provider, vm_name, request):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm = VM.factory(vm_name, provider, template_name=provider.data['small_template'])

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


@pytest.mark.uncollectif(
    lambda provider: provider.type != 'virtualcenter' and (provider.type != 'rhevm' or
          (provider.type == 'rhevm' and provider.version < 4)))
def test_snapshot_crud(test_vm, provider):
    """Tests snapshot crud

    Metadata:
        test_flag: snapshot, provision
    """
    if provider.type == 'rhevm':
        snapshot = new_snapshot(test_vm, has_name=False)
    else:
        snapshot = new_snapshot(test_vm)
    snapshot.create()
    snapshot.delete()


@pytest.mark.uncollectif(lambda provider: provider.type != 'virtualcenter')
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


@pytest.mark.meta(blockers=[1333566])
@pytest.mark.uncollectif(lambda provider: provider.type != 'virtualcenter')
def test_verify_revert_snapshot(test_vm, provider, soft_assert, register_event, request):
    """Tests revert snapshot

    Metadata:
        test_flag: snapshot, provision
    """
    snapshot1 = new_snapshot(test_vm)
    ip = snapshot1.vm.provider.mgmt.get_ip_address(snapshot1.vm.name)
    ssh_kwargs = {
        'username': credentials[provider.data['full_template']['creds']]['username'],
        'password': credentials[provider.data['full_template']['creds']]['password'],
        'hostname': ip
    }
    ssh = SSHClient(**ssh_kwargs)
    ssh.run_command('touch snapshot1.txt')
    snapshot1.create()
    ssh.run_command('touch snapshot2.txt')
    snapshot2 = new_snapshot(test_vm)
    snapshot2.create()
    snapshot1.revert_to()
    # Wait for the snapshot to become active
    logger.info('Waiting for vm %s to become active', snapshot1.name)
    wait_for(snapshot1.wait_for_snapshot_active, num_sec=300, delay=20, fail_func=sel.refresh)
    test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_OFF, timeout=720)
    register_event('VmOrTemplate', test_vm.name, ['request_vm_start', 'vm_start'])
    test_vm.power_control_from_cfme(option=test_vm.POWER_ON, cancel=False)
    navigate_to(test_vm.provider, 'Details')
    test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_ON, timeout=900)
    soft_assert(test_vm.find_quadicon().state == 'currentstate-on')
    soft_assert(
        test_vm.provider.mgmt.is_vm_running(test_vm.name), "vm not running")
    client = SSHClient(**ssh_kwargs)
    try:
        wait_for(lambda: client.run_command('test -e snapshot2.txt')[1] == 0, fail_condition=False)
        logger.info('Revert to snapshot %s successful', snapshot1.name)
    except:
        logger.info('Revert to snapshot %s Failed', snapshot1.name)


@pytest.mark.uncollectif(lambda provider: provider.type != 'virtualcenter')
@pytest.mark.meta(blockers=[1247664], automates=[1247664])
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
    miq_domain = Domain("ManageIQ (Locked)")
    miq_class = Class("Request", namespace=Namespace("System", domain=miq_domain))
    request_cls = miq_class.copy_to(domain)
    request.addfinalizer(request_cls.delete)
    method = Method("snapshot", data=method_contents, cls=request_cls)
    method.create()
    request.addfinalizer(method.delete)
    instance = Instance("snapshot", values={"meth5": "snapshot"}, cls=request_cls)
    instance.create()
    request.addfinalizer(instance.delete)

    # SIMULATE
    snap_name = fauxfactory.gen_alpha()
    snapshot = Vm.Snapshot(name=snap_name, parent_vm=test_vm)
    simulate(
        instance="Request", request="snapshot",
        attribute=["VM and Instance", test_vm.name],
        execute_methods=True,
        avp={"snap_name": snap_name})

    wait_for(snapshot.does_snapshot_exist, timeout="2m", delay=10)

    # Clean up if it appeared
    snapshot.delete()
