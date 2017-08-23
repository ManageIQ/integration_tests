# -*- coding: utf-8 -*-
import pytest
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage import object_store
from cfme.web_ui import mixins
from cfme.utils import testgen


pytestmark = pytest.mark.usefixtures("setup_provider")


pytest_generate_tests = testgen.generate([OpenStackProvider], scope="module")


@pytest.mark.tier(3)
def test_add_tag(request, provider, provisioning):
    """Tests object store edit tag

       Steps:
        * Click on quadicon.
        * On the details page, select ``Policy/Edit Tags`` and assign the tag to it.
        * Verify the tag is assigned.
        * Select ``Policy/Edit Tags`` and remove the tag.
    """
    obj_name = provisioning['cloud_object_store']
    cloud_obj = object_store.ObjectStore(name=obj_name)
    tag = ('Department', 'Accounting')
    cloud_obj.add_tag(tag, single_value=False)
    tagged_value = mixins.get_tags(tag="My Company Tags")
    assert tagged_value == ["Department: Accounting"], "Add tag failed"
    cloud_obj.untag(tag)


@pytest.mark.tier(3)
def test_remove_tag(request, provider, provisioning):
    """Tests object store edit tag

       Steps:
        * Click on quadicon.
        * On the details page, select ``Policy/Edit Tags`` and assign the tag to it.
        * Select ``Policy/Edit Tags`` and remove the tag.
        * Verify the tag is not present.
    """
    obj_name = provisioning['cloud_object_store']
    cloud_obj = object_store.ObjectStore(name=obj_name)
    tag = ('Department', 'Accounting')
    cloud_obj.add_tag(tag, single_value=False)
    tagged_value1 = mixins.get_tags(tag="My Company Tags")
    cloud_obj.untag(tag)
    tagged_value2 = mixins.get_tags(tag="My Company Tags")
    assert tagged_value1 != tagged_value2, "Remove tag failed"
