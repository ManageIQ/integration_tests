# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.object_store_object import ObjectStoreObjectCollection
from cfme.utils import testgen


pytestmark = pytest.mark.usefixtures("setup_provider")


pytest_generate_tests = testgen.generate([OpenStackProvider], scope="module")


@pytest.yield_fixture(scope="module")
def objects(appliance, provider):
    collection = ObjectStoreObjectCollection(appliance=appliance)
    objects = collection.all(provider)
    yield objects


@pytest.mark.tier(3)
def test_add_remove_tag(objects):
    object = random.choice(objects)

    # add tag with category Department and tag communication
    object.add_tag('Department', 'Communication')
    tag_available = object.get_tags()
    assert('Department' in tag_available and 'Communication' in tag_available)

    # remove assigned tag
    object.remove_tag('Department', 'Communication')
    tag_available = object.get_tags()
    assert('Department' not in tag_available and 'Communication' not in tag_available)