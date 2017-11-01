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


MANAGER_TYPE = ['Swift Manager', 'Cinder Manager']


@pytest.yield_fixture(params=MANAGER_TYPE,
                      ids=['object_manager', 'block_manager'])
def collection_manager(request, openstack_provider, appliance):
    if request.param == 'Swift Manager':
        collection = appliance.collections.object_managers
    else:
        collection = appliance.collections.block_managers
    manager_name = '{0} {1}'.format(openstack_provider.name, request.param)
    manager = collection.instantiate(name=manager_name, provider=openstack_provider)
    yield collection, manager


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_manager_navigation(collection_manager):
    collection, manager = collection_manager
    view = navigate_to(collection, 'All')
    assert view.is_displayed

    view = navigate_to(manager, 'Details')
    assert view.is_displayed

    manager.refresh()
