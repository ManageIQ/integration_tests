# -*- coding: utf-8 -*-
import pytest

import fauxfactory

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import error, testgen
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.rest import assert_response
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < '5.8'),
    pytest.mark.long_running,
    pytest.mark.tier(2),
    test_requirements.snapshot
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc,
        [VMwareProvider, OpenStackProvider])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.yield_fixture(scope='module')
def vm_obj(provider, setup_provider_modscope, small_template_modscope):
    """Creates new VM or instance"""
    vm_name = random_vm_name('snpsht')
    new_vm = VM.factory(vm_name, provider, template_name=small_template_modscope.name)

    if not provider.mgmt.does_vm_exist(vm_name):
        new_vm.create_on_provider(find_in_cfme=True, allow_skip='default')

    yield new_vm

    try:
        provider.mgmt.delete_vm(new_vm.name)
    except Exception:
        logger.warning("Failed to delete vm `{}`.".format(new_vm.name))


@pytest.fixture(scope='module')
def collection(appliance, provider):
    """Returns "vms" or "instances" collection based on provider type"""
    if provider.one_of(InfraProvider):
        return appliance.rest_api.collections.vms
    return appliance.rest_api.collections.instances


@pytest.yield_fixture(scope='function')
def vm_snapshot(appliance, collection, vm_obj):
    """Creates VM/instance snapshot using REST API

    Returns:
        Tuple with VM and snapshot resources in REST API
    """
    uid = fauxfactory.gen_alphanumeric(8)
    snap_name = 'snpshot_{}'.format(uid)
    vm = collection.get(name=vm_obj.name)
    vm.snapshots.action.create(
        name=snap_name,
        description='snapshot {}'.format(uid),
        memory=False)
    assert_response(appliance)
    snap, __ = wait_for(
        lambda: vm.snapshots.find_by(name=snap_name) or False,
        num_sec=600, delay=5)
    snap = snap[0]

    yield vm, snap

    collection.reload()
    to_delete = vm.snapshots.find_by(name=snap_name)
    if to_delete:
        vm.snapshots.action.delete(to_delete[0])


class TestRESTSnapshots(object):
    """Tests actions with VM/instance snapshots using REST API"""

    def test_create_snapshot(self, vm_snapshot):
        """Creates VM/instance snapshot using REST API

        Metadata:
            test_flag: rest
        """
        vm, snapshot = vm_snapshot
        vm.snapshots.get(name=snapshot.name)

    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_snapshot_from_detail(self, appliance, vm_snapshot, method):
        """Deletes VM/instance snapshot from detail using REST API

        Metadata:
            test_flag: rest
        """
        __, snapshot = vm_snapshot
        if method == 'post':
            del_action = snapshot.action.delete.POST
        else:
            del_action = snapshot.action.delete.DELETE

        del_action()
        assert_response(appliance)
        snapshot.wait_not_exists(num_sec=300, delay=5)

        # testing BZ 1466225
        with error.expected('ActiveRecord::RecordNotFound'):
            del_action()
        assert_response(appliance, http_status=404)

    def test_delete_snapshot_from_collection(self, appliance, vm_snapshot):
        """Deletes VM/instance snapshot from collection using REST API

        Metadata:
            test_flag: rest
        """
        vm, snapshot = vm_snapshot

        vm.snapshots.action.delete.POST(snapshot)
        assert_response(appliance)
        snapshot.wait_not_exists(num_sec=300, delay=5)

        # testing BZ 1466225
        with error.expected('ActiveRecord::RecordNotFound'):
            vm.snapshots.action.delete.POST(snapshot)
        assert_response(appliance, http_status=404)

    @pytest.mark.uncollectif(lambda provider:
            not provider.one_of(InfraProvider) or current_version() < '5.8')
    def test_revert_snapshot(self, appliance, vm_snapshot):
        """Reverts VM/instance snapshot using REST API

        Metadata:
            test_flag: rest
        """
        __, snapshot = vm_snapshot

        snapshot.action.revert()
        assert_response(appliance)
