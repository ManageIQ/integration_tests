# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.manager import StorageManagerDetailsView
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.storage,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope='module')
]


MANAGER_TYPE = ['Swift Manager', 'Cinder Manager']


@pytest.fixture(scope='module')
def provider_cleanup(provider):
    yield
    provider.delete_rest()
    provider.wait_for_delete()


@pytest.fixture(params=MANAGER_TYPE,
                      ids=['object_manager', 'block_manager'])
def collection_manager(request, openstack_provider, appliance):
    if request.param == 'Swift Manager':
        collection = appliance.collections.object_managers
    else:
        collection = appliance.collections.block_managers
    manager_name = '{0} {1}'.format(openstack_provider.name, request.param)
    manager = collection.instantiate(name=manager_name, provider=openstack_provider)
    yield collection, manager


def test_manager_navigation(collection_manager):
    collection, manager = collection_manager
    view = navigate_to(collection, 'All')
    assert view.is_displayed

    view = navigate_to(manager, 'Details')
    assert view.is_displayed

    manager.refresh()


def test_storage_manager_edit_tag(collection_manager):
    """ Test add and remove tag to storage manager

    prerequisites:
        * Storage provider

    Steps:
        * Add tag and check
        * Remove tag and check
    """

    manager = collection_manager[1]
    # add tag with category Department and tag communication
    added_tag = manager.add_tag()
    tag_available = manager.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    manager.remove_tag(added_tag)
    tag_available = manager.get_tags()
    assert not tag_available


def test_storage_manager_delete(collection_manager, provider_cleanup):
    """ Test delete storage manager

    prerequisites:
        * Storage provider

    Steps:
        * Delete storage manager from inventory
        * Assert flash message
        * Check storage manager exists or not
    """
    manager = collection_manager[1]
    manager.delete()
    view = manager.create_view(StorageManagerDetailsView)
    view.flash.assert_success_message(
        'Delete initiated for 1 Storage Manager from the CFME Database')
    assert not manager.exists
