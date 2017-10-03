# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils import testgen, version


pytestmark = pytest.mark.usefixtures("setup_provider")


pytest_generate_tests = testgen.generate([OpenStackProvider], scope="module")


@pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
@pytest.mark.tier(3)
def test_object_add_remove_tag(objects, provider):
    all_objects = objects.all()  # This call here doesn't filter at all
    obj = random.choice(all_objects)

    # add tag with category Department and tag communication
    obj.add_tag('Department', 'Communication')
    tag_available = obj.get_tags()
    assert 'Department' in tag_available and 'Communication' in tag_available

    # remove assigned tag
    obj.remove_tag('Department', 'Communication')
    tag_available = obj.get_tags()
    assert 'Department' not in tag_available and 'Communication' not in tag_available
