# -*- coding: utf-8 -*-
import random

import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.blockers import BZ

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


@pytest.mark.meta(blockers=[BZ(1648243, forced_streams=["5.9"])])
def test_add_remove_tag(containers):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
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
