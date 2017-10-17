"""Tests for Openstack cloud volumes"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils import testgen
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenStackProvider], scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.fixture(scope='module')
def volume_size():
    return 1


@pytest.yield_fixture(scope='function')
def volume(appliance, provider, volume_size):
    collection = appliance.collections.volumes
    volume = collection.create(name=fauxfactory.gen_alpha(),
                               storage_manager='{} Cinder Manager'.format(provider.name),
                               tenant=provider.get_yaml_data()['tenant'],
                               size=volume_size,
                               provider=provider)
    yield volume

    try:
        if volume.exists:
            volume.delete(wait=False)
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


def test_create_volume(volume, volume_size, provider):
    assert volume.exists
    assert volume.size == '{} GB'.format(volume_size)
    assert volume.tenant == provider.get_yaml_data()['tenant']


def test_edit_volume(volume):
    volume.edit(fauxfactory.gen_alpha())
    wait_for(volume.provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    assert volume.exists


def test_delete_volume(volume):
    volume.delete()
    assert not volume.exists
