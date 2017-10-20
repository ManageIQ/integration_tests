# -*- coding: utf-8 -*-
"""This module tests tagging of objects in different locations."""
import diaper
import pytest

from cfme.cloud.provider import CloudProvider
# from cfme.cloud.flavor import Flavor # Replace when all targets support widgets
# from cfme.cloud.availability_zone import AvailabilityZone # Replace all targets support widgets
from cfme.cloud.instance import Instance
from cfme.cloud.tenant import TenantCollection
from cfme.infrastructure.cluster import ClusterCollection
from cfme.infrastructure.datastore import DatastoreCollection
from cfme.infrastructure.host import HostCollection
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm, Template
from cfme.web_ui import mixins
from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.exceptions import ItemNotFound


param_classes = {
    # TODO: replace other classes with collections
    'Infra Providers': InfraProvider,
    'Infra VMs': Vm,
    'Infra Templates': Template,
    'Infra Hosts': HostCollection,
    'Infra Clusters': ClusterCollection,
    'Infra Stores': DatastoreCollection,

    'Cloud Providers': CloudProvider,
    'Cloud Instances': Instance,
    # 'Cloud Flavors': Flavor, # Test needs to be refactored along with tag mixin for widgets
    # 'Cloud Availabity Zones': AvailabilityZone,  # Add back when all classes support widgets
    'Cloud Tenants': TenantCollection
}

pytestmark = [
    pytest.mark.parametrize("location", param_classes),
    pytest.mark.tier(3)
]


def _navigate_and_check(location, appliance):
    if issubclass(param_classes[location], BaseCollection):
        cls_or_col = param_classes[location](appliance)
    else:
        cls_or_col = param_classes[location]
    view = navigate_to(cls_or_col, 'All')
    view.toolbar.view_selector.select('Grid View')
    try:
        entity = view.entities.get_first_entity()
        entity.check()
        return entity
    except ItemNotFound:
        pytest.skip("No Quadicon present, cannot test.")

# TODO Replace navigation and item selection with widgets when all tested classes have them


def _tag_item_through_selecting(request, location, tag, appliance):
    """Add a tag to an item with going through the details page.

    Prerequisities:
        * Have a tag category and tag created.
        * Be on the page you want to test.

    Steps:
        * Select any quadicon.
        * Select ``Policy/Edit Tags`` and assign the tag to it.
        * Click on the quadicon and verify the tag is assigned. (TODO)
        * Go back to the quadicon view and select ``Policy/Edit Tags`` and remove the tag.
        * Click on the quadicon and verify the tag is not present. (TODO)
    """
    _navigate_and_check(location, appliance)

    def _delete():
        # Ignoring the result of the check here
        _navigate_and_check(location, appliance)
        mixins.remove_tag(tag)
    request.addfinalizer(lambda: diaper(_delete))
    mixins.add_tag(tag)
    _delete()


def _tag_item_through_details(request, location, tag, appliance):
    """Add a tag to an item with going through the details page.

    Prerequisities:
        * Have a tag category and tag created.
        * Be on the page you want to test.

    Steps:
        * Click any quadicon.
        * On the details page, select ``Policy/Edit Tags`` and assign the tag to it.
        * Verify the tag is assigned. (TODO)
        * Select ``Policy/Edit Tags`` and remove the tag.
        * Verify the tag is not present. (TODO)
    """
    entity = _navigate_and_check(location, appliance)
    entity.click()
    request.addfinalizer(lambda: diaper(lambda: mixins.remove_tag(tag)))
    mixins.add_tag(tag)
    mixins.remove_tag(tag)


@pytest.mark.usefixtures('has_no_providers', scope='class')
class TestCloudTagVisibility():

    def test_cloud_tag_item_through_selecting(self, cloud_provider, request, location, tag,
                                              appliance):
        _tag_item_through_selecting(request, location, tag, appliance)

    def test_cloud_tag_item_through_details(self, cloud_provider, request, location, tag,
                                            appliance):
        _tag_item_through_details(request, location, tag, appliance)


@pytest.mark.usefixtures('has_no_providers', scope='class')
class TestInfraTagVisibility():

    def test_infra_tag_item_through_selecting(self, cloud_provider, request, location, tag,
                                              appliance):
        _tag_item_through_selecting(request, location, tag, appliance)

    def test_infra_tag_item_through_details(self, cloud_provider, request, location, tag,
                                            appliance):
        _tag_item_through_details(request, location, tag, appliance)
