# -*- coding: utf-8 -*-
"""This module tests tagging of objects in different locations."""
import diaper
import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.cluster import Cluster
from cfme.infrastructure.host import Host
from cfme.infrastructure.virtual_machines import Vm
from cfme.infrastructure.datastore import Datastore
from cfme.infrastructure.virtual_machines import Template
from cfme.cloud.provider import CloudProvider
from cfme.cloud.instance import Instance
from cfme.web_ui import Quadicon, mixins, toolbar as tb
from cfme.utils import providers
from cfme.utils.version import current_version


@pytest.fixture(scope="module")
def setup_first_provider():
    providers.setup_a_provider(prov_class="infra", validate=True, check_existing=True)
    providers.setup_a_provider(prov_class="cloud", validate=True, check_existing=True)


pytestmark = [
    pytest.mark.parametrize("location", [
        # Infrastructure
        InfraProvider, Cluster, Host, Datastore, Vm, Template,
        # Cloud
        CloudProvider, Instance,
        "clouds_availability_zones",  # todo: no navmazing for azone
        "clouds_flavors",  # todo: no navmazing for flavors
        "clouds_tenants",  # todo: no navmazing for tenants
        # "clouds_security_groups",  # Does not have grid view selector
    ]),
    pytest.mark.usefixtures("setup_first_provider"),
    pytest.mark.tier(3)
]


def nav_to(location):
    if isinstance(location, basestring):
        pytest.sel.force_navigate(location)
    else:
        navigate_to(location, 'All')


@pytest.mark.uncollectif(
    lambda location: location in {"clouds_tenants"} and current_version() < "5.4")
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
    nav_to(location)
    tb.select('Grid View')
    if not Quadicon.any_present():
        pytest.skip("No Quadicon present, cannot test.")
    Quadicon.select_first_quad()

    def _delete():
        nav_to(location)
        tb.select('Grid View')
        Quadicon.select_first_quad()
        mixins.remove_tag(tag)
    request.addfinalizer(lambda: diaper(_delete))
    mixins.add_tag(tag)
    _delete()


@pytest.mark.uncollectif(
    lambda location: location in {"clouds_tenants"} and current_version() < "5.4")
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
    nav_to(location)
    tb.select('Grid View')
    if not Quadicon.any_present():
        pytest.skip("No Quadicon present, cannot test.")
    pytest.sel.click(Quadicon.first())
    request.addfinalizer(lambda: diaper(lambda: mixins.remove_tag(tag)))
    mixins.add_tag(tag)
    mixins.remove_tag(tag)
