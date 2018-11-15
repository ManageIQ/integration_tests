"""Tests for Openstack cloud volumes"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.wait import wait_for, wait_for_decorator

pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenStackProvider], scope='module')
]


VOLUME_SIZE = 1


@pytest.fixture(scope='function')
def volume(appliance, provider):
    collection = appliance.collections.volumes
    storage_manager = '{} Cinder Manager'.format(provider.name)
    volume = collection.create(name=fauxfactory.gen_alpha(),
                               storage_manager=storage_manager,
                               tenant=provider.data['provisioning']['cloud_tenant'],
                               size=VOLUME_SIZE,
                               provider=provider)
    yield volume

    try:
        if volume.exists:
            volume.delete(wait=False)
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


@pytest.mark.regression
@pytest.fixture(scope='function')
def volume_with_type(appliance, provider):
    vol_type = provider.mgmt.capi.volume_types.create(name=fauxfactory.gen_alpha())
    volume_type = appliance.collections.volume_types.instantiate(vol_type.name, provider)

    @wait_for_decorator(delay=10, timeout=300,
                        message="Waiting for volume type to appear")
    def volume_type_is_displayed():
        volume_type.refresh()
        return volume_type.exists

    collection = appliance.collections.volumes
    storage_manager = '{} Cinder Manager'.format(provider.name)
    volume = collection.create(name=fauxfactory.gen_alpha(),
                               storage_manager=storage_manager,
                               tenant=provider.data['provisioning']['cloud_tenant'],
                               volume_type=volume_type.name,
                               size=VOLUME_SIZE,
                               provider=provider)
    yield volume

    if volume.exists:
        volume.delete(wait=False)

    if volume_type.exists:
        provider.mgmt.capi.volume_types.delete(vol_type)


@pytest.mark.regression
def test_create_volume(volume, provider):
    assert volume.exists
    assert volume.size == '{} GB'.format(VOLUME_SIZE)
    assert volume.tenant == provider.data['provisioning']['cloud_tenant']


@pytest.mark.regression
def test_edit_volume(volume, appliance):
    new_name = fauxfactory.gen_alpha()
    with update(volume):
        volume.name = new_name
    view = navigate_to(appliance.collections.volumes, 'All')
    assert view.entities.get_entity(name=new_name, surf_pages=True)


@pytest.mark.regression
def test_delete_volume(volume):
    volume.delete()
    assert not volume.exists


@pytest.mark.rfe
@pytest.mark.ignore_stream('5.9')
def test_create_volume_with_type(volume_with_type, provider):
    assert volume_with_type.exists
    assert volume_with_type.size == '{} GB'.format(VOLUME_SIZE)
    assert volume_with_type.tenant == provider.data['provisioning']['cloud_tenant']


@pytest.mark.rfe
@pytest.mark.ignore_stream('5.9')
def test_edit_volume_with_type(volume_with_type, appliance):
    new_name = fauxfactory.gen_alpha()
    with update(volume_with_type):
        volume_with_type.name = new_name
    view = navigate_to(appliance.collections.volumes, 'All')
    assert view.entities.get_entity(name=new_name, surf_pages=True)


@pytest.mark.rfe
@pytest.mark.ignore_stream('5.9')
def test_delete_volume_with_type(volume_with_type):
    volume_with_type.delete()
    assert not volume_with_type.exists
