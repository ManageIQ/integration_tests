import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.log import logger


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider(
        [OpenStackProvider],
        scope='module',
        required_fields=[['provisioning', 'cloud_tenant']]
    )
]

STORAGE_SIZE = 1


@pytest.fixture(scope='module')
def backup(appliance, provider):
    volume_collection = appliance.collections.volumes
    backup_collection = appliance.collections.volume_backups.filter({'provider': provider})
    # create new volume
    if appliance.version >= "5.11":   # has mandatory availability zone
        volume = volume_collection.create(name=fauxfactory.gen_alpha(start="vol_"),
                                          tenant=provider.data['provisioning']['cloud_tenant'],
                                          volume_size=STORAGE_SIZE,
                                          az=provider.data['provisioning']['availability_zone'],
                                          provider=provider)
    else:
        volume = volume_collection.create(name=fauxfactory.gen_alpha(start="vol_"),
                                          tenant=provider.data['provisioning']['cloud_tenant'],
                                          volume_size=STORAGE_SIZE,
                                          provider=provider)

    # create new backup for crated volume
    if volume.status == 'available':
        backup_name = fauxfactory.gen_alpha(start="bkup_")
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


@test_requirements.storage
@pytest.mark.tier(3)
def test_storage_volume_backup_create(backup):
    """
    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    assert backup.exists
    assert backup.size == STORAGE_SIZE


@pytest.mark.tier(3)
@test_requirements.tag
def test_storage_volume_backup_edit_tag_from_detail(backup):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    # add tag with category Department and tag communication
    added_tag = backup.add_tag()
    tag_available = backup.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    backup.remove_tag(added_tag)
    tag_available = backup.get_tags()
    assert not tag_available


@test_requirements.storage
@pytest.mark.tier(3)
def test_storage_volume_backup_delete(backup):
    """ Volume backup deletion method not support by 5.8

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """

    backup.parent.delete(backup)
    assert not backup.exists


@pytest.mark.manual
@test_requirements.storage
def test_storage_volume_backup_restore(backup):
    """
    Requires:
        test_storage_volume_backup[openstack]

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.7
        upstream: yes
        testSteps:
            1 . Go back to the summary page of the respective volume.
            2 . Restore Volume [configuration > Restore from backup of this cloud
            volume > select cloud volume backup]
        expectedResults:
            1.
            2. check in Task whether restored
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_volume_backup_restore_from_backup_page(backup):
    """
    Requires:
        test_storage_volume_backup[openstack]

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.9
        testSteps:
            1. Navigate to Volume Backups [Storage > Block Storage > Volume
            Backups]
            2. Select respective Volume backups
            3. Restore Volume [configuration > Restore backup to cloud volume
            4. Select Proper Volume to restore
        expectedResults:
            1.
            2.
            3.
            4. check in Task whether restored
    """
    pass
