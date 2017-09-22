# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.manager import ObjectManagerCollection, BlockManagerCollection
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate([CloudProvider])


pytestmark = [pytest.mark.tier(3),
              test_requirements.storage,
              pytest.mark.usefixtures('openstack_provider', 'setup_provider')]


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_block_manager_navigation(openstack_provider, appliance):
    """Simple test for navigation destinations"""

    collection = BlockManagerCollection(appliance=appliance)
    block_name = '{} Cinder Manager'.format(openstack_provider.name)
    block_manager = collection.instantiate(name=block_name, provider=openstack_provider)

    view = navigate_to(collection, 'All')
    assert view.is_displayed

    view = navigate_to(block_manager, 'Details')
    assert view.is_displayed

    block_manager.refresh()


@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_object_manager_navigation(openstack_provider, appliance):
    """Simple test for navigation destinations"""

    collection = ObjectManagerCollection(appliance=appliance)
    object_name = '{} Swift Manager'.format(openstack_provider.name)
    object_manager = collection.instantiate(name=object_name, provider=openstack_provider)

    view = navigate_to(collection, 'All')
    assert view.is_displayed

    view = navigate_to(object_manager, 'Details')
    assert view.is_displayed

    object_manager.refresh()
