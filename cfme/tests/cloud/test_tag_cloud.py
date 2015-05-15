# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.web_ui import Quadicon, mixins
from cfme.configure.configuration import Category, Tag
from utils.providers import setup_a_provider
from utils.randomness import generate_lowercase_random_string


@pytest.fixture(scope="module")
def setup_first_cloud_provider():
    setup_a_provider(prov_class="cloud", validate=True, check_existing=True)


@pytest.yield_fixture(scope="module")
def category():
    cg = Category(name=generate_lowercase_random_string(size=8),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    yield cg
    cg.delete()


@pytest.yield_fixture(scope="module")
def tag(category):
    tag = Tag(name=generate_lowercase_random_string(size=8),
              display_name=fauxfactory.gen_alphanumeric(32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


def test_tag_provider(setup_first_cloud_provider, tag):
    """Add a tag to a provider
    """
    pytest.sel.force_navigate('clouds_providers')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)


def test_tag_vm(setup_first_cloud_provider, tag):
    """Add a tag to a vm
    """
    pytest.sel.force_navigate('clouds_instances_by_provider')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
