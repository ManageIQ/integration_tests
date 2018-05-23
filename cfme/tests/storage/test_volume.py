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

    Polarion:
        assignee: None
        initialEstimate: None
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

    Polarion:
        assignee: None
        initialEstimate: None
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

    Polarion:
        assignee: None
        initialEstimate: None
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
