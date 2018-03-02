# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from selenium.common.exceptions import TimeoutException

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.storage,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope='module')
]

STORAGE_SIZE = 1


@pytest.yield_fixture(scope='module')
def volume(appliance, provider):
    # create new volume
    volume_collection = appliance.collections.volumes
    manager_name = '{} Cinder Manager'.format(provider.name)
    volume = volume_collection.create(name=fauxfactory.gen_alpha(),
                                      storage_manager=manager_name,
                                      tenant=provider.data['provisioning']['cloud_tenant'],
                                      size=STORAGE_SIZE,
                                      provider=provider)
    yield volume

    try:
        if volume.exists:
            volume.delete(wait=True)
    except Exception as e:
        logger.warning("{name}:{msg} Volume deletion - skipping...".format(
            name=type(e).__name__,
            msg=str(e)))


@pytest.yield_fixture(scope='function')
def snapshot(appliance, provider, volume):
    # create new snapshot for crated volume
    snapshot_collection = appliance.collections.volume_snapshots.filter({'provider': provider})
    snapshot_name = fauxfactory.gen_alpha()
    volume.create_snapshot(snapshot_name)
    snapshot = snapshot_collection.instantiate(snapshot_name, provider)
    yield snapshot

    try:
        if snapshot.exists:
            snapshot.delete()
    except Exception as e:
        logger.warning("{name}:{msg}: Snapshot deletion - skipping...".format(
            name=type(e).__name__,
            msg=str(e)))


@pytest.mark.tier(3)
def test_storage_snapshot_create_cancelled_validation(volume):
    """ Test snapshot create cancelled

    prerequisites:
        * Storage Volume

    Steps:
        * Navigate to Snapshot create window
        * Fill snapshot name
        * Click Cancel button
        * Assert flash message
    """

    snapshot_name = fauxfactory.gen_alpha()
    volume.create_snapshot(snapshot_name, cancel=True)


@pytest.mark.tier(3)
def test_storage_snapshot_create_reset_validation(volume):
    """ Test snapshot create reset button validation

    prerequisites:
        * Storage Volume

    Steps:
        * Navigate to Snapshot create window
        * Fill snapshot name
        * Click Reset button
        * Assert flash message
    """

    snapshot_name = fauxfactory.gen_alpha()
    volume.create_snapshot(snapshot_name, reset=True)


@pytest.mark.tier(1)
def test_storage_volume_snapshot_crud(appliance, provider, volume):
    """ Test storage snapshot crud

    prerequisites:
        * Volume

    Steps:
        * Create a snapshot
        * Delete a snapshot
    """

    snapshot_collection = appliance.collections.volume_snapshots.filter({'provider': provider})

    # create new snapshot
    snapshot_name = fauxfactory.gen_alpha()
    volume.create_snapshot(snapshot_name)
    snapshot = snapshot_collection.instantiate(snapshot_name, provider)

    try:
        wait_for(lambda: snapshot.status == 'available',
                 delay=20, timeout=1200, fail_func=snapshot.refresh)
    except TimeoutException:
        logger.error('Snapshot Creation fails:'
                     'TimeoutException due to status not available (=error)')

    assert snapshot.exists
    assert snapshot.size == STORAGE_SIZE

    # deleting snapshot
    snapshot.delete()
    assert not snapshot.exists


@pytest.mark.tier(3)
def test_storage_volume_snapshot_edit_tag_from_detail(snapshot):
    """ Test tags for snapshot

    prerequisites:
        * snapshot

    Steps:
        * Navigate to Snapshot Detail page
        * Add new Tag
        * Remove Tag
    """

    # add tag with category Department and tag communication
    snapshot.add_tag('Department', 'Communication')
    tag_available = snapshot.get_tags()
    assert tag_available[0].display_name == 'Communication'
    assert tag_available[0].category.display_name == 'Department'

    # remove assigned tag
    snapshot.remove_tag('Department', 'Communication')
    tag_available = snapshot.get_tags()
    assert not tag_available
