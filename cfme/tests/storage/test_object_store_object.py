# -*- coding: utf-8 -*-
import tempfile

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope="module"),
]


@pytest.fixture(scope="module")
def storage_object(appliance, provider):
    collection = appliance.collections.object_store_objects.filter({"provider": provider})
    objs = collection.all()

    if not objs:
        # Note: Like to avoid creation with api client multiple time.
        # Maintaining at least one object as creation not possible with CFME UI for OSP.

        cont_key = "cont_{}".format(fauxfactory.gen_alpha(3))
        provider.mgmt.create_container(cont_key)

        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf")
        obj = collection.instantiate(
            key="obj_{}".format(fauxfactory.gen_alpha(3)), provider=provider
        )
        provider.mgmt.create_object(
            container_name=cont_key, path=temp_file.name, object_name=obj.key
        )
        collection.manager.refresh()
        wait_for(lambda: obj.exists, delay=30, timeout=1200, fail_func=provider.browser.refresh)
        return obj
    else:
        return objs[0]


def test_object_add_remove_tag(storage_object):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    # add tag with category Department and tag communication
    added_tag = storage_object.add_tag()
    tag_available = storage_object.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    storage_object.remove_tag(added_tag)
    tag_available = storage_object.get_tags()
    assert not tag_available


@pytest.mark.manual
@test_requirements.storage
def test_storage_object_store_object_remove():
    """
    Requirs:
    OpenstackProvider
    1) Navigate to Object Store Object [Storage > Object Storage > Object
    Store Objects]
    2) Select objects for removal
    3) Remove [Configuration > Remove Object Storage Objects from
    Inventory]
    4) Verify object removed or not

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_object_store_object_edit_tag_openstack():
    """
    Requirs:
    OpenstackProvider
    1) Navigate to Object Store Object [Storage > Object Storage > Object
    Store Objects]
    2) go to summery pages of any object
    2) add tag : [Policy > Edit Tags]
    3) Verify the tag is assigned
    4) remove tag: [Policy > Edit Tags]
    5) Verify the tag is removed

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
    """
    pass
