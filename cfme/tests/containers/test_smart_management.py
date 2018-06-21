import random

import pytest
from cfme.containers.provider import (ContainersProvider, ContainersTestItem,
    refresh_and_navigate)
from cfme.containers.image import Image, ImageCollection
from cfme.containers.project import Project, ProjectCollection
from cfme.containers.image_registry import (ImageRegistry,
                                            ImageRegistryCollection)
from cfme.containers.node import Node, NodeCollection
from cfme.containers.pod import Pod, PodCollection
from cfme.containers.template import Template, TemplateCollection
from cfme.containers.container import Container, ContainerCollection
from cfme.containers.provider import ContainersProviderCollection
from cfme.utils.log import create_sublogger
from cfme.utils.wait import wait_for

from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]
logger = create_sublogger("smart_management")

TEST_ITEMS = [
    pytest.mark.polarion('CMP-9948')(ContainersTestItem(
        Container, 'CMP-9948', collection_obj="containers")),
    pytest.mark.polarion('CMP-10320')(ContainersTestItem(
        Template, 'CMP-10320', collection_obj="container_templates")),
    pytest.mark.polarion('CMP-9992')(ContainersTestItem(
        ImageRegistry, 'CMP-9992', collection_obj="container_image_registries")),
    pytest.mark.polarion('CMP-9981')(ContainersTestItem(
        Image, 'CMP-9981', collection_obj="container_images")),
    pytest.mark.polarion('CMP-9964')(ContainersTestItem(
        Node, 'CMP-9964', collection_obj="container_nodes")),
    pytest.mark.polarion('CMP-9932')(ContainersTestItem(
        Pod, 'CMP-9932', collection_obj="container_pods")),
    pytest.mark.polarion('CMP-9870')(ContainersTestItem(
        Project, 'CMP-9870', collection_obj="container_projects")),
    pytest.mark.polarion('CMP-9854')(ContainersTestItem(
        ContainersProvider, 'CMP-9854', collection_obj="containers_providers"))
]


@pytest.fixture(scope="function")
def get_entity(collection):
    return random.choice(collection.all())


@pytest.fixture(scope="function")
def get_clean_entity(**kwargs):
    collection = kwargs.get("collection", None)
    entity = kwargs.get("entity", get_entity(collection))

    tags = entity.get_tags()
    entity.remove_tags(tags)
    return entity

def get_object_name(obj):
    return obj.__module__.title().split(".")[-1]

def wait_for_tag(obj_inst):
    # Waiting for some tag to appear at "My Company Tags" and return pop'ed last tag
    def is_tag():
        view = refresh_and_navigate(obj_inst, 'Details')
        return view.entities.smart_management.read().get('My Company Tags', [])
    last_tag = wait_for(is_tag, fail_condition=[], num_sec=30, delay=5).out
    logger.debug("Last tag type: {t}".format(t=type(last_tag)))
    return last_tag.pop() if isinstance(last_tag, list) else last_tag


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
@pytest.mark.meta(blockers=[BZ(1479412,
                               forced_streams=['5.7'],
                               unblock=lambda test_item: test_item.obj != Container)])
def test_smart_management_add_tag(appliance, provider, test_item):
    logger.debug("Setting smart mgmt tag to {obj_type}".format(obj_type=test_item.obj.__name__))

    # validate no tag set to project
    obj_collection = getattr(appliance.collections, test_item.collection_obj)
    obj_inst = get_clean_entity(entity=provider) if test_item.obj is ContainersProvider \
        else get_clean_entity(collection=obj_collection)

    logger.debug('Selected object is "{obj_name}"'.format(obj_name=obj_inst.name))

    # Config random tag for object
    tag = obj_collection.add_tag([obj_inst])
    logger.debug("Set function result: {tag}".format(tag=tag))


    all_tags = obj_inst.get_tags()
    logger.debug("Current exist tag: {tag}".format(tag=tag))

    # Validate tag wsa set successfully
    assert len(all_tags) == 1, "Fail to set a tag for {obj_type}".format(
        obj_type=get_object_name(test_item.obj))
    actual_tags_on_instance = all_tags.pop()

    # Validate tag value
    assert tag.display_name == actual_tags_on_instance.display_name, \
        "Tag value not correctly configured"
