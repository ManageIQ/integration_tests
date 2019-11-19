import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    test_requirements.rest,
    pytest.mark.provider([VMwareProvider, RHEVMProvider, OpenStackProvider], scope='module'),
    pytest.mark.meta(
        blockers=[
            BZ(
                1712850,
                forced_streams=["5.11"],
                unblock=lambda provider: not provider.one_of(OpenStackProvider),
            )
        ]
    ),
]


@pytest.fixture(scope='module')
def collection(appliance, provider):
    """Returns "vms" or "instances" collection based on provider type."""
    if provider.one_of(InfraProvider):
        return appliance.rest_api.collections.vms
    return appliance.rest_api.collections.instances


@pytest.fixture(scope='module')
def vm(provider, appliance, collection, setup_provider_modscope, small_template_modscope):
    """Creates new VM or instance."""
    vm_name = random_vm_name('snpsht')
    prov_collection = provider.appliance.provider_based_collection(provider)
    new_vm = prov_collection.instantiate(vm_name,
                                         provider,
                                         small_template_modscope.name)

    if not collection.find_by(name=vm_name):
        new_vm.create_on_provider(find_in_cfme=True, allow_skip='default')

    vm_rest = collection.get(name=vm_name)
    yield vm_rest

    vms = appliance.rest_api.collections.vms.find_by(name=vm_name)
    if vms:
        vm = vms[0]
        vm.action.delete()
        vm.wait_not_exists(num_sec=600, delay=5)
    new_vm.cleanup_on_provider()


def _delete_snapshot(vm, description):
    """Deletes snapshot if it exists."""
    to_delete = vm.snapshots.find_by(description=description)
    if to_delete:
        snap = to_delete[0]
        snap.action.delete()
        snap.wait_not_exists(num_sec=300, delay=5)


@pytest.fixture(scope='function')
def vm_snapshot(request, appliance, collection, vm):
    """Creates VM/instance snapshot using REST API.

    Returns:
        Tuple with VM and snapshot resources in REST API
    """
    uid = fauxfactory.gen_alphanumeric(8)
    snap_desc = 'snapshot {}'.format(uid)
    request.addfinalizer(lambda: _delete_snapshot(vm, snap_desc))
    vm.snapshots.action.create(
        name='test_snapshot_{}'.format(uid),
        description=snap_desc,
        memory=False,
    )
    assert_response(appliance)
    snap, __ = wait_for(
        lambda: vm.snapshots.find_by(description=snap_desc) or False,
        num_sec=800,
        delay=5,
        message='snapshot creation',
    )
    snap = snap[0]

    return vm, snap


class TestRESTSnapshots(object):
    """Tests actions with VM/instance snapshots using REST API."""

    @pytest.mark.rhv2
    def test_create_snapshot(self, vm_snapshot):
        """Creates VM/instance snapshot using REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        vm, snapshot = vm_snapshot
        vm.snapshots.get(description=snapshot.description)

    @pytest.mark.rhv3
    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_snapshot_from_detail(self, vm_snapshot, method):
        """Deletes VM/instance snapshot from detail using REST API.

        Testing BZ 1466225

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        __, snapshot = vm_snapshot
        delete_resources_from_detail([snapshot], method=method, num_sec=300, delay=5)

    @pytest.mark.rhv3
    def test_delete_snapshot_from_collection(self, vm_snapshot):
        """Deletes VM/instance snapshot from collection using REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        vm, snapshot = vm_snapshot
        delete_resources_from_collection(
            [snapshot], vm.snapshots, not_found=True, num_sec=300, delay=5)

    def test_delete_snapshot_race(self, request, appliance, collection, vm):
        """Tests creation of snapshot while delete is in progress.

        Testing race condition described in BZ 1550551

        Expected result is either success or reasonable error message.
        Not expected result is success where no snapshot is created.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        # create and delete snapshot #1
        __, snap1 = vm_snapshot(request, appliance, collection, vm)
        snap1.action.delete()

        # create snapshot #2 without waiting for delete
        # of snapshot #1 to finish
        try:
            vm_snapshot(request, appliance, collection, vm)
        except AssertionError as err:
            # The `vm_snapshot` calls `assert_response` that checks status of the Task.
            # AssertionError is raised when Task failed and Task message is included
            # in error message.
            # Error message can be different after BZ 1550551 is fixed.
            if 'Please wait for the operation to finish' not in str(err):
                raise

    @pytest.mark.rhv2
    @pytest.mark.provider([VMwareProvider, RHEVMProvider])
    def test_revert_snapshot(self, appliance, provider, vm_snapshot):
        """Reverts VM/instance snapshot using REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        __, snapshot = vm_snapshot

        snapshot.action.revert()
        if provider.one_of(RHEVMProvider):
            assert_response(appliance, success=False)
            result = appliance.rest_api.response.json()
            assert 'Revert is allowed only when vm is down' in result['message']
        else:
            assert_response(appliance)
