# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.manager import StorageManagerDetailsView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.storage,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([EC2Provider, OpenStackProvider], scope="module"),
    pytest.mark.uncollectif(
        lambda manager, provider: provider.one_of(EC2Provider) and "object_manager" in manager,
        reason="Object Storage not supported by EC2Provider",
    ),
]


@pytest.fixture(scope="function")
def provider_cleanup(provider):
    yield
    if provider.exists:
        provider.delete_rest()
        provider.wait_for_delete()


@pytest.fixture(params=["object_manager", "block_manager"])
def manager(request, appliance, provider):
    if request.param == "object_manger":
        collection = appliance.collections.object_managers.filter({"provider": provider})
    else:
        collection = appliance.collections.block_managers.filter({"provider": provider})
    yield collection.all()[0]


def test_manager_navigation(manager):
    """
    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    view = navigate_to(manager.parent, "All")
    assert view.is_displayed

    view = navigate_to(manager, "Details")
    assert view.is_displayed

    manager.refresh()


@pytest.mark.meta(blockers=[BZ(1648243, forced_streams=["5.9"])])
def test_storage_manager_edit_tag(manager):
    """ Test add and remove tag to storage manager

    prerequisites:
        * Storage provider

    Steps:
        * Add tag and check
        * Remove tag and check

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """

    # add tag with category Department and tag communication
    added_tag = manager.add_tag()
    tag_available = manager.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    manager.remove_tag(added_tag)
    tag_available = manager.get_tags()
    assert not tag_available


def test_storage_manager_delete(manager, provider_cleanup):
    """ Test delete storage manager

    prerequisites:
        * Storage provider

    Steps:
        * Delete storage manager from inventory
        * Assert flash message
        * Check storage manager exists or not

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    manager.delete()
    view = manager.create_view(StorageManagerDetailsView)
    view.flash.assert_success_message(
        "Delete initiated for 1 Storage Manager from the CFME Database"
    )
    assert not manager.exists
