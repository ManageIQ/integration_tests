# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope="module"),
]


@pytest.mark.meta(blockers=[BZ(1648243, forced_streams=["5.9"])])
def test_object_add_remove_tag(appliance, provider):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
    """
    collection = appliance.collections.object_store_objects.filter({'provider': provider})
    all_objects = collection.all()
    if all_objects is None:
        pytest.skip('No object store object in collection {} for provider {}'
                    .format(collection, provider))
    obj = random.choice(all_objects)

    # add tag with category Department and tag communication
    added_tag = obj.add_tag()
    tag_available = obj.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    obj.remove_tag(added_tag)
    tag_available = obj.get_tags()
    assert not tag_available
