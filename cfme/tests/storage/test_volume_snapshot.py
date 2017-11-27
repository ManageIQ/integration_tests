# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils import version
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
def snapshot(appliance, provider):
    volume_collection = appliance.collections.volumes
    storage_manager = version.pick({'5.8': '{} Cinder Manager'.format(provider.name),
                                    version.LOWEST: None})
    snapshot_collection = appliance.collections.volume_snapshots.filter({'provider': provider})

    # create new volume
    volume = volume_collection.create(name=fauxfactory.gen_alpha(),
                                      storage_manager=storage_manager,
                                      tenant=provider.data['provisioning']['cloud_tenant'],
                                      size=STORAGE_SIZE,
                                      provider=provider)

    # create new snapshot for crated volume
    snapshot_name = fauxfactory.gen_alpha()
    volume.create_snapshot(snapshot_name)
    snapshot = snapshot_collection.instantiate(snapshot_name, provider)

    yield snapshot

    try:
        if snapshot.exists:
            snapshot_collection.delete(snapshot)
        if volume.exists:
            volume.delete(wait=False)
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
def test_storage_volume_snapshot_create(snapshot):
    wait_for(lambda: snapshot.status == 'available',
             delay=20, timeout=800, fail_func=snapshot.refresh)

    assert snapshot.exists
    assert snapshot.size == STORAGE_SIZE


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
def test_storage_volume_snapshot_edit_tag_from_detail(snapshot):
    # add tag with category Department and tag communication
    snapshot.add_tag('Department', 'Communication')
    tag_available = snapshot.get_tags()
    assert tag_available[0].display_name == 'Communication'
    assert tag_available[0].category.display_name == 'Department'

    # remove assigned tag
    snapshot.remove_tag('Department', 'Communication')
    tag_available = snapshot.get_tags()
    assert not tag_available


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
def test_storage_volume_snapshot_delete(snapshot):
    snapshot.delete()
    assert not snapshot.exists
