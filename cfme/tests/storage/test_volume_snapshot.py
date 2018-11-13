# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError
from cfme.storage.volume import VolumeDetailsView, VolumeSnapshotView

pytestmark = [
    test_requirements.storage,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope='module')
]

STORAGE_SIZE = 1


@pytest.fixture(scope='module')
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


@pytest.fixture(scope='function')
def snapshot(volume):
    # create new snapshot for crated volume
    snapshot_name = fauxfactory.gen_alpha()
    snapshot = volume.create_snapshot(snapshot_name)

    try:
        wait_for(lambda: snapshot.status == 'available',
                 delay=20, timeout=1200, fail_func=snapshot.refresh)
    except TimedOutError:
        logger.error('Snapshot Creation fails:'
                     'TimeoutException due to status not available (=error)')
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
    view = volume.create_view(VolumeDetailsView)
    view.wait_displayed(timeout='10s')
    view.flash.assert_message(
        'Snapshot of Cloud Volume "{}" was cancelled by the user'.format(volume.name))


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
    view = volume.create_view(VolumeSnapshotView)
    view.flash.assert_message('All changes have been reset')


@pytest.mark.tier(1)
def test_storage_volume_snapshot_crud(volume):
    """ Test storage snapshot crud

    prerequisites:
        * Volume

    Steps:
        * Create a snapshot
        * Delete a snapshot
    """

    # create new snapshot
    initial_snapshot_count = volume.snapshots_count
    snapshot_name = fauxfactory.gen_alpha()
    snapshot = volume.create_snapshot(snapshot_name)
    view = volume.create_view(VolumeDetailsView)
    view.wait_displayed(timeout='10s')
    view.flash.assert_success_message(
        'Snapshot for Cloud Volume "{}" created'.format(volume.name))

    # check for volume relationship tables snapshot count
    try:
        wait_for(lambda: volume.snapshots_count > initial_snapshot_count,
                 delay=20, timeout=1000, fail_func=volume.refresh)
    except TimedOutError:
        logger.error('Snapshot count increment fails')

    # check for status of snapshot
    try:
        wait_for(lambda: snapshot.status == 'available',
                 delay=20, timeout=1200, fail_func=snapshot.refresh)
    except TimedOutError:
        logger.error('Snapshot Creation fails:'
                     'TimeoutException due to status not available (=error)')

    assert snapshot.exists
    assert snapshot.size == STORAGE_SIZE

    # deleting snapshot
    snapshot.delete()
    assert not snapshot.exists


@pytest.mark.meta(blockers=[BZ(1648243, forced_streams=["5.9"])])
@pytest.mark.tier(3)
def test_storage_volume_snapshot_edit_tag_from_detail(snapshot, tag):
    """ Test tags for snapshot

    prerequisites:
        * snapshot

    Steps:
        * Navigate to Snapshot Detail page
        * Add new Tag
        * Remove Tag
    """

    # add tag with category Department and tag communication
    snapshot.add_tag(tag)
    tag_available = snapshot.get_tags()
    assert tag_available[0].display_name == tag.display_name
    assert tag_available[0].category.display_name == tag.category.display_name

    # remove assigned tag
    snapshot.remove_tag(tag)
    tag_available = snapshot.get_tags()
    assert not tag_available
