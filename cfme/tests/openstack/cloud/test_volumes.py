"""Tests for Openstack cloud volumes"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils import testgen
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenStackProvider], scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]

VOLUME_SIZE = 1


@pytest.yield_fixture(scope='function')
def volume(appliance, provider):
    collection = appliance.collections.volumes
    volume = collection.create(name=fauxfactory.gen_alpha(),
                               storage_manager='{} Cinder Manager'.format(provider.name),
                               tenant=provider.data.get('tenant'),
                               size=VOLUME_SIZE,
                               provider=provider)
    yield volume

    try:
        if volume.exists:
            volume.delete(wait=False)
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


def test_create_volume(volume, provider):
    assert volume.exists
    assert volume.size == '{} GB'.format(VOLUME_SIZE)
    assert volume.tenant == provider.data.get('tenant')


def test_edit_volume(volume):
    volume.edit(fauxfactory.gen_alpha())
    wait_for(volume.provider.is_refreshed, func_kwargs=dict(refresh_delta=5), timeout=600)
    assert volume.exists


def test_delete_volume(volume):
    volume.delete()
    assert not volume.exists
