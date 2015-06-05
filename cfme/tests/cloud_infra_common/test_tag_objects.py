# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.web_ui import Quadicon, mixins, toolbar as tb
from cfme.configure.configuration import Category, Tag
from utils import providers


@pytest.fixture(scope="module")
def setup_first_provider():
    providers.setup_a_provider(
        prov_class="infra", validate=True, check_existing=True, delete_failure=True)
    providers.setup_a_provider(
        prov_class="cloud", validate=True, check_existing=True, delete_failure=True)


pytestmark = [
    pytest.mark.parametrize("location", [
        # Infrastructure
        "infrastructure_providers",
        "infrastructure_clusters",
        "infrastructure_hosts",
        "infrastructure_datastores",
        "infra_vms",
        "infra_templates",

        # Cloud
        "clouds_providers",
        "clouds_instances",
        "clouds_availability_zones",
        "clouds_flavors",
        "clouds_tenants",
        # "clouds_security_groups",  # Does not have grid view selector
    ]),
    pytest.mark.usefixtures("setup_first_provider")
]


@pytest.yield_fixture(scope="module")
def category():
    cg = Category(name=fauxfactory.gen_alpha(8).lower(),
                  description=fauxfactory.gen_alphanumeric(length=32),
                  display_name=fauxfactory.gen_alphanumeric(length=32))
    cg.create()
    yield cg
    cg.delete()


@pytest.yield_fixture(scope="module")
def tag(category):
    tag = Tag(name=fauxfactory.gen_alpha(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(length=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


def test_tag_item_through_selecting(location, tag):
    """Add a tag to an item."""
    pytest.sel.force_navigate(location)
    tb.set_vms_grid_view()
    if not Quadicon.any_present:
        pytest.skip("No Quadicon present, cannot test.")
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
    tb.set_vms_grid_view()
    Quadicon.select_first_quad()  # It goes back to the list view.
    mixins.remove_tag(tag)


def test_tag_item_through_details(location, tag):
    """Add a tag to an item."""
    pytest.sel.force_navigate(location)
    tb.set_vms_grid_view()
    if not Quadicon.any_present:
        pytest.skip("No Quadicon present, cannot test.")
    pytest.sel.click(Quadicon.first())
    mixins.add_tag(tag)
    mixins.remove_tag(tag)
