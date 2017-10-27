# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils import testgen, version


pytestmark = pytest.mark.usefixtures("setup_provider")


pytest_generate_tests = testgen.generate([OpenStackProvider], scope="module")


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
def test_storage_volume_backup_edit_tag_from_detail(appliance, provider):
    collection = appliance.collections.volume_backups.filter({'provider': provider})
    backups = collection.all()
    backup = random.choice(backups)

    # add tag with category Department and tag communication
    backup.add_tag('Department', 'Communication')
    tag_available = backup.get_tags()
    assert tag_available[0].display_name == 'Communication'
    assert tag_available[0].category.display_name == 'Department'

    # remove assigned tag
    backup.remove_tag('Department', 'Communication')
    tag_available = backup.get_tags()
    assert tag_available == []
