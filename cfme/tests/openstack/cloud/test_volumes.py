"""Tests for Openstack cloud volumes"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenStackProvider], scope='module')
]


VOLUME_SIZE = 1


@pytest.yield_fixture(scope='function')
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


@pytest.mark.meta(blockers=[BZ(1502609, forced_streams=["5.9"])])
def test_create_volume(volume, provider):
    assert volume.exists
    assert volume.size == '{} GB'.format(VOLUME_SIZE)
    assert volume.tenant == provider.data['provisioning']['cloud_tenant']


@pytest.mark.meta(blockers=[BZ(1502609, forced_streams=["5.9"])])
def test_edit_volume(volume, appliance):
    new_name = fauxfactory.gen_alpha()
    volume.edit(new_name)
    view = navigate_to(appliance.collections.volumes, 'All')
    assert view.entities.get_entity(name=new_name, surf_pages=True)


@pytest.mark.meta(blockers=[BZ(1502609, forced_streams=["5.9"])])
def test_delete_volume(volume):
    volume.delete()
    assert not volume.exists
