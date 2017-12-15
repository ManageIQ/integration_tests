# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope="module"),
]


def test_object_add_remove_tag(appliance, provider):
    collection = appliance.collections.object_store_objects.filter({'provider': provider})
    all_objects = collection.all()
    obj = random.choice(all_objects)

    # add tag with category Department and tag communication
    obj.add_tag('Department', 'Communication')
    tag_available = obj.get_tags()
    assert tag_available[0].display_name == 'Communication'
    assert tag_available[0].category.display_name == 'Department'

    # remove assigned tag
    obj.remove_tag('Department', 'Communication')
    tag_available = obj.get_tags()
    assert not tag_available
