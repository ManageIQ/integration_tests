import pytest

from cfme.web_ui import Quadicon, mixins
from cfme.configure.configuration import Category, Tag
from utils.randomness import generate_lowercase_random_string, generate_random_string


@pytest.yield_fixture(scope="module")
def category():
    cg = Category(name=generate_lowercase_random_string(size=8),
                  description=generate_random_string(size=32),
                  display_name=generate_random_string(size=32))
    cg.create()
    yield cg
    cg.delete()


@pytest.yield_fixture(scope="module")
def tag(category):
    tag = Tag(name=generate_lowercase_random_string(size=8),
              display_name=generate_random_string(size=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


def test_tag_provider(setup_cloud_providers, tag):
    """Add a tag to a provider
    """
    pytest.sel.force_navigate('clouds_providers')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)


def test_tag_vm(setup_cloud_providers, tag):
    """Add a tag to a vm
    """
    pytest.sel.force_navigate('clouds_instances')
    Quadicon.select_first_quad()
    mixins.add_tag(tag)
