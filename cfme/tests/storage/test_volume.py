# -*- coding: utf-8 -*-
import pytest
import fauxfactory

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.volume import VolumeAllView
from cfme.utils.update import update

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.storage,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope='module'),
]

STORAGE_SIZE = 1


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
