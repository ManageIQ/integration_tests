import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.manager import StorageManagerVolumeAllView
from cfme.storage.volume import VolumeDetailsView
from cfme.storage.volume import VolumeSnapshotView
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.storage,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.provider(
        [EC2Provider, OpenStackProvider],
        scope='module',
        required_fields=[['provisioning', 'cloud_tenant']]
    )
]

STORAGE_SIZE = 1


@pytest.fixture(scope='module')
def volume(appliance, provider):
    # create new volume
    volume_collection = appliance.collections.volumes
    name = fauxfactory.gen_alpha(start="vol_")
    volume_kwargs = {
        'name': name,
        'volume_size': STORAGE_SIZE,
        'provider': provider,
        'cancel': False
    }
    if provider.one_of(OpenStackProvider):
        volume_kwargs['tenant'] = provider.data['provisioning']['cloud_tenant']
        if appliance.version >= "5.11":  # has mandatory availability zone
            volume_kwargs['az'] = provider.data['provisioning']['availability_zone']

    elif provider.one_of(EC2Provider):
        volume_kwargs['az'] = f"{provider.region}a"
        volume_kwargs['volume_type'] = 'General Purpose SSD (GP2)'
    else:
        return False

    volume = volume_collection.create(**volume_kwargs)
    assert volume.exists
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
    snapshot_name = fauxfactory.gen_alpha(start="snap_")
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


@pytest.mark.parametrize('snapshot_create_from', [True, False], ids=['from_manager', 'from_volume'])
@pytest.mark.tier(3)
def test_storage_snapshot_create_cancelled_validation(volume, snapshot_create_from):
    """ Test snapshot create cancelled

    prerequisites:
        * Storage Volume

    Steps:
        * Navigate to Snapshot create window
        * Fill snapshot name
        * Click Cancel button
        * Assert flash message

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/4h
        casecomponent: Cloud
    """

    snapshot_name = fauxfactory.gen_alpha(start="snap_")
    volume.create_snapshot(snapshot_name, cancel=True, from_manager=snapshot_create_from)
    if snapshot_create_from:
        view = volume.browser.create_view(StorageManagerVolumeAllView, additional_context={
            'object': volume.parent.manager}, wait='10s')
    else:
        view = volume.create_view(VolumeDetailsView, wait='10s')
    view.flash.assert_message(
        f'Snapshot of Cloud Volume "{volume.name}" was cancelled by the user')


@pytest.mark.parametrize('snapshot_create_from', [True, False], ids=['from_manager', 'from_volume'])
@pytest.mark.tier(3)
def test_storage_snapshot_create_reset_validation(volume, snapshot_create_from):
    """ Test snapshot create reset button validation

    prerequisites:
        * Storage Volume

    Steps:
        * Navigate to Snapshot create window
        * Fill snapshot name
        * Click Reset button
        * Assert flash message

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/4h
        casecomponent: Cloud
    """

    snapshot_name = fauxfactory.gen_alpha(start="snap_")
    volume.create_snapshot(snapshot_name, reset=True, from_manager=snapshot_create_from)
    view = volume.create_view(VolumeSnapshotView)
    view.flash.assert_message('All changes have been reset')


@pytest.mark.parametrize('snapshot_create_from', [True, False], ids=['from_manager', 'from_volume'])
@pytest.mark.tier(1)
def test_storage_volume_snapshot_crud(volume, provider, snapshot_create_from):
    """ Test storage snapshot crud
    prerequisites:
        * Volume

    Polarion:
        assignee: gtalreja
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Cloud
        testSteps:
            1. Create new snapshot
            2. Updates that snapshot
            3. Delete delete that snapshot
    """

    # create new snapshot
    initial_snapshot_count = volume.snapshots_count
    snapshot_name = fauxfactory.gen_alpha(start="snap_")
    snapshot = volume.create_snapshot(snapshot_name, from_manager=snapshot_create_from)
    view = volume.create_view(VolumeDetailsView, wait='10s')
    view.flash.assert_success_message(
        f'Snapshot for Cloud Volume "{volume.name}" created')

    # check for volume relationship tables snapshot count
    try:
        wait_for(lambda: volume.snapshots_count > initial_snapshot_count,
                 delay=20, timeout=1000, fail_func=volume.refresh)
    except TimedOutError:
        logger.error('Snapshot count increment fails')

    # check for status of snapshot
    status = 'completed' if provider.one_of(EC2Provider) else 'available'
    try:
        wait_for(lambda: snapshot.status == status,
                 delay=20, timeout=1200, fail_func=snapshot.refresh)
    except TimedOutError:
        logger.error('Snapshot Creation fails:'
                     'TimeoutException due to status not available (=error)')

    assert snapshot.exists
    assert snapshot.size == STORAGE_SIZE

    # deleting snapshot
    snapshot.delete()
    assert not snapshot.exists


@pytest.mark.tier(3)
@test_requirements.tag
def test_storage_volume_snapshot_edit_tag_from_detail(snapshot, tag):
    """ Test tags for snapshot

    prerequisites:
        * snapshot

    Steps:
        * Navigate to Snapshot Detail page
        * Add new Tag
        * Remove Tag

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Configuration
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
