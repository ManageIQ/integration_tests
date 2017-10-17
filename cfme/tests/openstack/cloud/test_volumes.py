"""Tests for Openstack cloud volumes"""

import fauxfactory
import pytest

from cfme.exceptions import ItemNotFound
from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider

from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger


pytest_generate_tests = testgen.generate([OpenStackProvider], scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]



@pytest.fixture(scope='module')
def volume_size(appliance, provider):
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
            volume.delete()
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


def test_create_volume(volume, volume_size, provider):
