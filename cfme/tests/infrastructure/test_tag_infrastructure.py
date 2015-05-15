# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.web_ui import Quadicon, mixins
from cfme.configure.configuration import Category, Tag
from utils import providers
from utils.randomness import generate_lowercase_random_string


@pytest.fixture(scope="module")
def setup_first_provider():
    providers.setup_a_provider(prov_class="infra", validate=True, check_existing=True)


pytestmark = [
    pytest.mark.parametrize("location", [
        "infrastructure_providers",
        "infrastructure_clusters",
        "infrastructure_hosts",
        "infrastructure_datastores",
        "infra_vms",
        "infra_templates",
    ]),
    pytest.mark.usefixtures("setup_first_provider")
]


@pytest.yield_fixture(scope="module")
def category():
    cg = Category(name=generate_lowercase_random_string(size=8),
                  description=fauxfactory.gen_alphanumeric(length=32),
                  display_name=fauxfactory.gen_alphanumeric(length=32))
    cg.create()
    yield cg
    cg.delete()


@pytest.yield_fixture(scope="module")
def tag(category):
    tag = Tag(name=generate_lowercase_random_string(size=8),
              display_name=fauxfactory.gen_alphanumeric(length=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


def test_tag_infra_item_through_selecting(location, tag):
    """Add a tag to a infra item
    """
    pytest.sel.force_navigate(location)
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
    Quadicon.select_first_quad()  # It goes back to the list view.
    mixins.remove_tag(tag)


def test_tag_infra_item_through_details(location, tag):
    """Add a tag to a infra item
    """
    pytest.sel.force_navigate(location)
    pytest.sel.click(Quadicon.first())
    mixins.add_tag(tag)
    mixins.remove_tag(tag)
