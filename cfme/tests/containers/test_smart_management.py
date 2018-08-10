import re
import random

import pytest
from cfme.configure.configuration.region_settings import Tag
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
from cfme.utils.log import create_sublogger
from cfme.utils.wait import wait_for
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]
logger = create_sublogger("smart_management")

TEST_ITEMS = [
    ContainersTestItem(Container, 'container_smart_man', collection_obj=ContainerCollection),
    ContainersTestItem(Template, 'template_smart_man', collection_obj=TemplateCollection),
    ContainersTestItem(ImageRegistry, 'image_registry_smart_man',
                       collection_obj=ImageRegistryCollection),
    ContainersTestItem(Image, 'image_smart_man', collection_obj=ImageCollection),
    ContainersTestItem(Node, 'node_smart_man', collection_obj=NodeCollection),
    ContainersTestItem(Pod, 'pod_smart_man', collection_obj=PodCollection),
    ContainersTestItem(Project, 'project_smart_man', collection_obj=ProjectCollection),
    ContainersTestItem(ContainersProvider, 'container_provider_smart_man', collection_obj=None)
]


def get_object_name(obj):
    return obj.__module__.title().split(".")[-1]


def set_random_tag(instance):
    view = navigate_to(instance, 'EditTags')
    logger.debug("Setting random tag")
    random_cat = random.choice(view.form.tag_category.all_options).text
    view.form.tag_category.select_by_visible_text(random_cat)  # In order to get the right tags list
    logger.debug("Selected category {cat}".format(cat=random_cat))
    random_tag = random.choice([op for op in view.form.tag_name.all_options
                                if "select" not in op.text.lower()]).text
    logger.debug("Selected value {tag}".format(tag=random_tag))
    tag = Tag(display_name=random_tag, category=random_cat)
    instance.add_tag(tag, details=False)
    logger.debug("Tag configuration was saved")
    return tag


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
@pytest.mark.meta(blockers=[
    BZ(1609541, forced_streams=["5.9"]),
    BZ(1601915, forced_streams=["5.10"])
])
def test_smart_management_add_tag(provider, appliance, test_item):
    logger.debug("Setting smart mgmt tag to {obj_type}".format(obj_type=test_item.obj.__name__))
    # validate no tag set to project
    obj_inst = (provider if test_item.obj is ContainersProvider
                else test_item.collection_obj(appliance).get_random_instances().pop())

    logger.debug('Selected object is "{obj_name}"'.format(obj_name=obj_inst.name))

    regex = r"([\w\s|\-|\*]+:([\w\s|\-|\*])+)|(No.*assigned)"
    try:
        # Remove all previous configured tags for given object
        logger.debug('Starting cleaning old tags from '
                    'object "{obj_name}"'.format(obj_name=obj_inst.name))
        obj_inst.remove_tags(obj_inst.get_tags())
        logger.debug("All smart management tags was removed successfully")
    except RuntimeError:
        logger.debug("Fail to remove tags, checking if no tag set")

        # Validate old tags formatting
        assert re.match(regex, wait_for_tag(obj_inst).text_value), (
            "Tag formatting is invalid! ")
        logger.debug("No tag was set, continuing to main test")

    # Config random tag for object\
    random_tag_set = set_random_tag(obj_inst)

    logger.debug("Fetching tag info for selected object")
    # validate new tag format
    tag_display_text = wait_for_tag(obj_inst)
    logger.debug("Tag info: {info}".format(info=tag_display_text))

    assert re.match(regex, tag_display_text), "Tag formatting is invalid! "
    actual_tags_on_instance = obj_inst.get_tags()

    # Validate tag seted successfully
    assert len(actual_tags_on_instance) == 1, "Fail to set a tag for {obj_type}".format(
        obj_type=get_object_name(test_item.obj))
    actual_tags_on_instance = actual_tags_on_instance.pop()

    # Validate tag value
    assert actual_tags_on_instance.display_name == random_tag_set.display_name, \
        "Tag value not correctly configured"
