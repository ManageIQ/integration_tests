# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.log import logger


pytestmark = [pytest.mark.ignore_stream("upstream"),
              pytest.mark.usefixtures('setup_provider'),
              pytest.mark.provider([OpenStackProvider], scope='module')]

STORAGE_SIZE = 1


@pytest.fixture(scope='module')
def backup(appliance, provider):
    volume_collection = appliance.collections.volumes
    storage_manager = '{} Cinder Manager'.format(provider.name)
    backup_collection = appliance.collections.volume_backups.filter({'provider': provider})

    # create new volume
    volume = volume_collection.create(name=fauxfactory.gen_alpha(),
                                      storage_manager=storage_manager,
                                      tenant=provider.data['provisioning']['cloud_tenant'],
                                      size=STORAGE_SIZE,
                                      provider=provider)

    # create new backup for crated volume
    if volume.status == 'available':
        backup_name = fauxfactory.gen_alpha()
        volume.create_backup(backup_name)
        backup = backup_collection.instantiate(backup_name, provider)
        yield backup
    else:
        pytest.skip('Skipping volume backup tests, provider side volume creation fails')

    try:
        if backup.exists:
            backup_collection.delete(backup)
        if volume.exists:
            volume.delete(wait=False)
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


@pytest.mark.tier(3)
def test_storage_volume_backup_create(backup):
    assert backup.exists
    assert backup.size == STORAGE_SIZE


@pytest.mark.tier(3)
def test_storage_volume_backup_edit_tag_from_detail(backup):
    # add tag with category Department and tag communication
    added_tag = backup.add_tag()
    tag_available = backup.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    backup.remove_tag(added_tag)
    tag_available = backup.get_tags()
    assert not tag_available


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda appliance: appliance.version < '5.9')
def test_storage_volume_backup_delete(backup):
    """ Volume backup deletion method not support by 5.8 """

    backup.parent.delete(backup)
    assert not backup.exists
