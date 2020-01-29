import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.manager import ObjectManagerCollection
from cfme.storage.manager import ProviderStorageManagerAllView
from cfme.storage.manager import StorageManagerDetailsView
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.storage,
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([EC2Provider, OpenStackProvider], scope="module"),
    pytest.mark.uncollectif(lambda manager, provider:
                            provider.one_of(EC2Provider) and "object_managers" in manager,
                            reason="Object Storage not supported by EC2Provider"),
]


@pytest.fixture(scope="function")
def provider_cleanup(provider):
    yield
    if provider.exists:
        provider.delete_rest()
        provider.wait_for_delete()


@pytest.fixture(params=["object_managers", "block_managers"])
def manager(request, appliance, provider):
    try:
        collection = getattr(appliance.collections, request.param).filter({"provider": provider})
    except AttributeError:
        pytest.skip('Appliance collections did not include parametrized storage manager type ({})'
                    .format(request.param))
    yield collection.all()[0]


def test_manager_navigation(manager):
    """
    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: critical
    """
    view = navigate_to(manager.parent, "All")
    assert view.is_displayed

    view = navigate_to(manager, "Details")
    assert view.is_displayed

    manager.refresh()


def test_storage_manager_edit_tag(manager):
    """ Test add and remove tag to storage manager

    prerequisites:
        * Storage provider

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: medium
        testSteps:
            * Add tag and check
            * Remove tag and check
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

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: medium
        testSteps:
            * Delete storage manager from inventory
            * Assert flash message
            * Check storage manager exists or not
    """
    manager.delete()
    view = manager.create_view(StorageManagerDetailsView)
    view.flash.assert_success_message(
        "Delete initiated for 1 Storage Manager from the CFME Database"
    )
    assert not manager.exists


def test_storage_manager_navigation_from_cloudprovider(manager, provider):
    """ Test whether Storage Manager is accessible from Cloud Provider

    prerequisites:
        * Storage provider

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        testSteps:
            * Go to Cloud Provider summary
            * Check whether Cloud Provider has any Storage Managers
            * Click on Storage managers
            * Select Storage Manager from list
            * Check whether Storage Manager's Summary is displayed correctly
    """
    view = navigate_to(provider, 'Details')
    manager_count = int(view.entities.summary("Relationships").get_text_of("Storage Managers"))
    assert manager_count > 0
    view.entities.summary("Relationships").click_at("Storage Managers")
    storage_view = view.browser.create_view(ProviderStorageManagerAllView)
    assert storage_view.entities.table.row_count == manager_count
    storage_view.paginator.find_row_on_pages(storage_view.entities.table,
                                             Name=manager.name).click()
    storage_detail_view = storage_view.browser.create_view(StorageManagerDetailsView)
    assert storage_detail_view.title.text == "{} (Summary)".format(manager.name)


@pytest.mark.meta(automates=[1650086])
def test_storage_manager_quadicon_numbers(manager, provider, provider_cleanup, request):
    """ Test whether Storage Manager QuadIcon shows correct numbers
    Bugzilla: 1650086

    prerequisites:
        * Storage provider

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/8h
        casecomponent: Cloud
        caseimportance: high
        testSteps:
            * Go to Cloud Provider List
            * Check Quadicon
            * Compare quadicon with provider's relationships
    """
    view = navigate_to(manager.parent, 'All')
    view.toolbar.view_selector.select("Grid View")
    quad_data = view.entities.get_entities_by_keys(name=manager.name)[0].data.get('quad', {})

    if isinstance(manager.parent, ObjectManagerCollection):
        quad_container_count = int(quad_data["topLeft"]["text"])
        view = navigate_to(manager, 'Details')
        container_count = int(view.entities.relationships.get_text_of(
            "Cloud object store containers"))
        assert quad_container_count == container_count
    else:
        quad_volume_count = int(quad_data["topLeft"]["text"])
        quad_snapshot_count = int(quad_data["topRight"]["text"])
        view = navigate_to(manager, 'Details')
        volume_count = int(view.entities.relationships.get_text_of("Cloud Volumes"))
        snapshot_count = int(view.entities.relationships.get_text_of("Cloud Volume Snapshots"))
        assert quad_volume_count == volume_count
        assert quad_snapshot_count == snapshot_count
