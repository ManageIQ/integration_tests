# -*- coding: utf-8 -*-
"""This module tests tagging of objects in different locations."""
import diaper
import pytest

from cfme.cloud.provider import CloudProvider
from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.flavor import Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.tenant import Tenant
from cfme.infrastructure.cluster import Cluster
from cfme.infrastructure.datastore import Datastore
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm, Template
from cfme.web_ui import Quadicon, mixins, toolbar as tb
from utils import providers
from utils.appliance.implementations.ui import navigate_to


@pytest.fixture(scope="module")
def setup_first_provider():
    providers.setup_a_provider(prov_class="infra", validate=True, check_existing=True)
    providers.setup_a_provider(prov_class="cloud", validate=True, check_existing=True)


param_classes = {
    'Infra Providers': InfraProvider,
    'Infra VMs': Vm,
    'Infra Templates': Template,
    'Infra Hosts': Host,
    'Infra Clusters': Cluster,
    'Infra Stores': Datastore,

    'Cloud Providers': CloudProvider,
    'Cloud Instances': Instance,
    'Cloud Availabity Zones': AvailabilityZone,
    'Cloud Flavors': Flavor,
    'Cloud Tenants': Tenant
}

pytestmark = [
    pytest.mark.parametrize("location", param_classes),
    pytest.mark.usefixtures("setup_first_provider"),
    pytest.mark.tier(3)
]


def navigate_and_check(location):
    navigate_to(param_classes[location], 'All')
    tb.select('Grid View')
    return Quadicon.any_present()


def test_tag_item_through_selecting(request, location, tag):
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
    if not navigate_and_check(location):
        pytest.skip("No Quadicon present, cannot test.")
    Quadicon.select_first_quad()

    def _delete():
        # Ignoring the result of the check here
        navigate_and_check(location)
        Quadicon.select_first_quad()
        mixins.remove_tag(tag)
    request.addfinalizer(lambda: diaper(_delete))
    mixins.add_tag(tag)
    _delete()


def test_tag_item_through_details(request, location, tag):
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
    if not navigate_and_check(location):
        pytest.skip("No Quadicon present, cannot test.")
    pytest.sel.click(Quadicon.first())
    request.addfinalizer(lambda: diaper(lambda: mixins.remove_tag(tag)))
    mixins.add_tag(tag)
    mixins.remove_tag(tag)
