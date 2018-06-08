# -*- coding: utf-8 -*-
import pytest
import fauxfactory

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.volume import VolumeAllView
from cfme.utils.log import logger
from cfme.utils.update import update


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.storage,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope='module'),
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


def test_storage_volume_create_cancelled_validation(appliance, provider):
    """ Test Attach instance to storage volume cancelled

    prerequisites:
        * Storage provider

    Steps:
        * Navigate to storage add volume page
        * Click Cancel button
        * Assert flash message
    """
    volume_collection = appliance.collections.volumes
    manager_name = '{} Cinder Manager'.format(provider.name)
    volume_collection.create(name=fauxfactory.gen_alpha(),
                             storage_manager=manager_name,
                             tenant=provider.data['provisioning']['cloud_tenant'],
                             size=STORAGE_SIZE,
                             provider=provider,
                             cancel=True)

    view = volume_collection.create_view(VolumeAllView)
    view.flash.assert_message('Add of new Cloud Volume was cancelled by the user')


@pytest.mark.tier(1)
def test_storage_volume_crud(appliance, provider):
    """ Test storage volume crud

    prerequisites:
        * Storage provider

    Steps:
        * Crate new volume
        * Delete volume
    """
    # create volume
    volume_collection = appliance.collections.volumes
    manager_name = '{} Cinder Manager'.format(provider.name)
    volume = volume_collection.create(name=fauxfactory.gen_alpha(),
                                      storage_manager=manager_name,
                                      tenant=provider.data['provisioning']['cloud_tenant'],
                                      size=STORAGE_SIZE,
                                      provider=provider)
    assert volume.exists

    # update volume
    old_name = volume.name
    new_name = fauxfactory.gen_alpha()
    with update(volume):
        volume.name = new_name

    with update(volume):
        volume.name = old_name

    # delete volume
    volume.delete(wait=True)
    assert not volume.exists


def test_storage_volume_edit_tag(volume):
    """ Test add and remove tag to storage volume

    prerequisites:
        * Storage Volume

    Steps:
        * Add tag and check
        * Remove tag and check
    """

    # add tag with category Department and tag communication
    added_tag = volume.add_tag()
    tag_available = volume.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    volume.remove_tag(added_tag)
    tag_available = volume.get_tags()
    assert not tag_available


def test_multiple_cloud_volumes_tag_edit(appliance, soft_assert):
    """Test tag can be added to multiple volumes at once"""
    all_volumes = appliance.collections.volumes.all()
    volumes = all_volumes[:3] if len(all_volumes) > 4 else all_volumes
    assigned_tag = appliance.collections.volumes.add_tag(volumes)
    for item in volumes:
        tag_available = item.get_tags()
        soft_assert(any(
            tag.category.display_name == assigned_tag.category.display_name and
            tag.display_name == assigned_tag.display_name for tag in tag_available), (
            'Tag is not assigned to volume {}'.format(item.name)))

    # remove tags to multiple items at once
    appliance.collections.volumes.remove_tag(volumes, assigned_tag)
    for item in volumes:
        soft_assert(not item.get_tags())
