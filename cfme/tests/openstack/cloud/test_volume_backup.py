"""Tests for Openstack cloud volume Backups"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider])
]


VOLUME_SIZE = 1


@pytest.fixture(scope='function')
def volume_backup(appliance, provider):
    volume_collection = appliance.collections.volumes
    storage_manager = '{} Cinder Manager'.format(provider.name)
    backup_collection = appliance.collections.volume_backups.filter({'provider': provider})

    # create new volume
    volume = volume_collection.create(name=fauxfactory.gen_alpha(),
                                      storage_manager=storage_manager,
                                      tenant=provider.data['provisioning']['cloud_tenant'],
                                      size=VOLUME_SIZE,
                                      provider=provider)

    # create new backup for crated volume
    if volume.status == 'available':
        backup_name = fauxfactory.gen_alpha()
        volume.create_backup(backup_name)
        volume_backup = backup_collection.instantiate(backup_name, provider)
        yield volume_backup
    else:
        pytest.skip('Skipping volume backup tests, provider side volume creation fails')

    try:
        if volume_backup.exists:
            backup_collection.delete(volume_backup)
        if volume.exists:
            volume.delete(wait=False)
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


@pytest.fixture(scope='function')
def incremental_backup(volume_backup, provider):
    backup_collection = provider.appliance.collections.volume_backups.filter({'provider': provider})
    volume = volume_backup.appliance.collections.volumes.instantiate(volume_backup.volume, provider)

    # create incremental backup for a volume with existing backup
    backup_name = fauxfactory.gen_alpha()
    volume.create_backup(backup_name, incremental=True)
    incremental_backup = backup_collection.instantiate(backup_name, provider)
    yield incremental_backup

    try:
        if incremental_backup.exists:
            backup_collection.delete(incremental_backup)
    except Exception:
        logger.warning('Exception during volume backup deletion - skipping..')


def test_create_volume_backup(volume_backup):
    assert volume_backup.exists
    assert volume_backup.size == VOLUME_SIZE


def test_create_volume_incremental_backup(incremental_backup):
    assert incremental_backup.exists
    assert incremental_backup.size == VOLUME_SIZE
