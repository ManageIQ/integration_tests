import random

import pytest
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.project import Project
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import Node
from cfme.containers.pod import Pod
from cfme.containers.template import Template
from cfme.containers.container import Container
from cfme.utils.wait import wait_for

from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]

TEST_ITEMS = [
    pytest.mark.polarion('CMP-9948')(ContainersTestItem(
        Container, 'CMP-9948', collection_obj="containers", get_entity_by="name")),
    pytest.mark.polarion('CMP-10320')(ContainersTestItem(
        Template, 'CMP-10320', collection_obj="container_templates", get_entity_by="name")),
    pytest.mark.polarion('CMP-9992')(ContainersTestItem(
        ImageRegistry, 'CMP-9992', collection_obj="container_image_registries",
        get_entity_by="host")),
    pytest.mark.polarion('CMP-9964')(ContainersTestItem(
        Node, 'CMP-9964', collection_obj="container_nodes", get_entity_by="name")),
    pytest.mark.polarion('CMP-9932')(ContainersTestItem(
        Pod, 'CMP-9932', collection_obj="container_pods", get_entity_by="name")),
    pytest.mark.polarion('CMP-9870')(ContainersTestItem(
        Project, 'CMP-9870', collection_obj="container_projects", get_entity_by="name")),
    pytest.mark.polarion('CMP-9854')(ContainersTestItem(
        ContainersProvider, 'CMP-9854', collection_obj="containers_providers",
        get_entity_by="name"))
]


@pytest.fixture
def get_entity(collection):

    # Map all object by name
    mapping = {item.name: item for item in collection.all()}

    # Filter only the unique items
    unique_items = [key for key in set(mapping.keys()) if mapping.keys().count(key) == 1]

    # If there is at least one  unique item
    if unique_items:
        # Return a random item
        selected_item_name = random.choice(unique_items)
        return mapping[selected_item_name]
    else:
        pytest.skip("No unique item was found")


@pytest.mark.meta(blockers=[BZ(1479412,
                               forced_streams=['5.7'],
                               unblock=lambda test_item: test_item.obj != Container)])
@pytest.fixture
def get_clean_entity(**kwargs):
    collection = kwargs.get("collection", None)
    entity = kwargs.get("entity") if "entity" in kwargs else get_entity(collection)

    tags = entity.get_tags()
    entity.remove_tags(tags)
    return entity


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
@pytest.mark.meta(blockers=[
    BZ(1609541, forced_streams=["5.9"]),
    BZ(1601915, forced_streams=["5.10"])
])
def test_smart_management_add_tag(provider, appliance, test_item):
    logger.debug("Setting smart mgmt tag to {obj_type}".format(obj_type=test_item.obj.__name__))

    # validate no tag set to project
    obj_collection = getattr(appliance.collections, test_item.collection_obj)
    obj_inst = (get_clean_entity(entity=provider)
        if test_item.obj is ContainersProvider else get_clean_entity(collection=obj_collection))

    # Config random tag for object
    tag = obj_collection.add_tag([obj_inst], get_entity_by=test_item.get_entity_by)

    all_tags = wait_for(obj_inst.get_tags, num_sec=30, delay=5).out

    # Validate tag wsa set successfully
    assert len(all_tags) == 1, "Wrong tag count fount for {obj}".format(obj=obj_inst.PLURAL)
    actual_tags_on_instance = all_tags.pop()

    # Validate tag value
    assert tag.display_name == actual_tags_on_instance.display_name, (
        "Tag value not correctly configured")
