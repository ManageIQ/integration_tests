# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope="module"),
]


@pytest.yield_fixture(scope="module")
def containers(appliance, provider):
    collection = appliance.collections.object_store_containers.filter({'provider': provider})
    containers = collection.all()
    # TODO add create method and remove pytest skip as BZ 1490320 fix
    yield containers if containers else pytest.skip("No Containers Available")


def test_add_remove_tag(containers):
    container = random.choice(containers)

    # add tag with category Department and tag communication
    container.add_tag('Department', 'Communication')
    tag_available = container.get_tags()
    assert tag_available[0].display_name == 'Communication'
    assert tag_available[0].category.display_name == 'Department'

    # remove assigned tag
    container.remove_tag('Department', 'Communication')
    tag_available = container.get_tags()
    assert not tag_available
