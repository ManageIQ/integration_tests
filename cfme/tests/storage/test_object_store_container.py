# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope="module"),
]


@pytest.fixture(scope="module")
def containers(appliance, provider):
    collection = appliance.collections.object_store_containers.filter({'provider': provider})
    containers = collection.all()
    # TODO add create method and remove pytest skip as BZ 1490320 fix
    yield containers if containers else pytest.skip("No Containers Available")


def test_add_remove_tag(containers):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    container = random.choice(containers)

    # add tag with category Department and tag communication
    added_tag = container.add_tag()
    tag_available = container.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    container.remove_tag(added_tag)
    tag_available = container.get_tags()
    assert not tag_available
