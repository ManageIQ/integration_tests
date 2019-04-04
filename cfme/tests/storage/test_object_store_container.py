# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope="module"),
]


@pytest.fixture(scope="module")
def container(appliance, provider):
    collection = appliance.collections.object_store_containers.filter({"provider": provider})
    conts = collection.all()

    if not conts:
        # Note: Like to avoid creation with api client multiple time.
        # Maintaining at least one container as creation not possible with UI for OSP.

        cont = collection.instantiate(
            key="cont_{}".format(fauxfactory.gen_alpha(3)), provider=provider
        )
        provider.mgmt.create_container(cont.key)
        collection.manager.refresh()
        wait_for(lambda: cont.exists, delay=30, timeout=1200, fail_func=provider.browser.refresh)
        return cont
    else:
        return conts[0]


def test_add_remove_tag(container):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
    """

    # add tag with category Department and tag communication
    added_tag = container.add_tag()
    tag_available = container.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    container.remove_tag(added_tag)
    tag_available = container.get_tags()
    assert not tag_available
