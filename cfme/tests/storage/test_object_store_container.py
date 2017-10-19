# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils import testgen


pytestmark = pytest.mark.usefixtures("setup_provider")


pytest_generate_tests = testgen.generate([OpenStackProvider], scope="module")


@pytest.yield_fixture(scope="module")
def containers(appliance, provider):
    collection = appliance.collections.object_store_containers.filter({'provider': provider})
    containers = collection.all()
    # TODO add create method and remove pytest skip as BZ 1490320 fix
    yield containers if containers else pytest.skip("No Containers Available")


@pytest.mark.tier(3)
def test_add_remove_tag(containers):
    container = random.choice(containers)

    # add tag with category Department and tag communication
    container.add_tag('Department', 'Communication')
    tag_available = container.get_tags()
    assert 'Department' in tag_available and 'Communication' in tag_available

    # remove assigned tag
    container.remove_tag('Department', 'Communication')
    tag_available = container.get_tags()
    assert 'Department' not in tag_available and 'Communication' not in tag_available
