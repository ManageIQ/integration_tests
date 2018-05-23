"""Tests for Openstack cloud volumes"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.update import update

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


def test_create_volume(volume, provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    assert volume.exists
    assert volume.size == '{} GB'.format(VOLUME_SIZE)
    assert volume.tenant == provider.data['provisioning']['cloud_tenant']


def test_edit_volume(volume, appliance):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    new_name = fauxfactory.gen_alpha()
    with update(volume):
        volume.name = new_name
    view = navigate_to(appliance.collections.volumes, 'All')
    assert view.entities.get_entity(name=new_name, surf_pages=True)


def test_delete_volume(volume):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    volume.delete()
    assert not volume.exists
