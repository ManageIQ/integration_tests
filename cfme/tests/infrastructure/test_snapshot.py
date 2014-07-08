import pytest
import time
import random
from cfme.infrastructure.virtual_machines import Vm
from utils.conf import cfme_data
from cfme.web_ui import flash
from utils import testgen
from utils.log import logger
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.wait import wait_for, TimedOutError

#Work in progress
# GLOBAL vars
random_vm_test = []    # use the same values(provider/vm) for all the quadicon tests


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    new_idlist = []
    new_argvalues = []
    """for i, argvalue_tuple in enumerate(argvalues):
        provider_data = cfme_data['management_systems'][
            argvalue_tuple[argnames.index('provider_key')]]
        #print provider_data
        if provider_data.get('type', False) != 'virtualcenter':
            continue
    """
    if 'random_snpsht_mgt_vm' in metafunc.fixturenames:
        if random_vm_test:
            argnames, new_argvalues, new_idlist = random_vm_test
        else:
            single_index = random.choice(range(len(idlist)))
            new_idlist = [idlist[single_index]]
            new_argvalues = argvalues[single_index]
            argnames.append('random_snpsht_mgt_vm')
            new_argvalues.append('')
            new_argvalues = [new_argvalues]
            random_vm_test.append(argnames)
            random_vm_test.append(new_argvalues)
            random_vm_test.append(new_idlist)
    else:
        new_idlist = idlist
        new_argvalues = argvalues
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="class")
def vm_name():
    return "test_snpsht_" + generate_random_string()


@pytest.fixture(scope="class")
def test_vm(request, provider_crud, provider_mgmt, vm_name):
    '''Fixture to provision appliance to the provider being tested if necessary'''
    vm = Vm(vm_name, provider_crud)

    request.addfinalizer(vm.delete_from_provider)

    if not provider_mgmt.does_vm_exist(vm_name):
        vm.create(timeout_in_minutes=15)
    return vm


@pytest.fixture(scope="class")
def new_snapshot(test_vm):
    snapshot = Vm.Snapshot(name="snpshot_" + generate_random_string(), description="snapshot", memory=False, parent_vm=test_vm)
    return snapshot


@pytest.mark.usefixtures("random_snpsht_mgt_vm")
def test_snapshot_crud(new_snapshot):
        new_snapshot.create()
        new_snapshot.delete()


def test_delete_all_snapshots(new_snapshot):
        new_snapshot.create()
        new_snapshot.create()
        new_snapshot.delete_all()


def test_revert_snapshot(new_snapshot):
        new_snapshot.create()
        new_snapshot.create()
        new_snapshot.revert_to()


def test_verify_snapshot(new_snapshot):
        new_snapshot.create()
        ip = new_snapshot.vm.provider_crud.get_ip_address(new_snapshot.vm.name)
        print ip
        ssh = SSHClient(hostname=ip, port="22")
        ssh.run_command('touch ~/tmp.file1')
