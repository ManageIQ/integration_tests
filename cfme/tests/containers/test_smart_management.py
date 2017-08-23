import re
import random
import pytest
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.version import current_version
from cfme.web_ui import toolbar, AngularSelect, form_buttons
from cfme.configure.configuration import Tag
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.node import Node
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.template import Template
from cfme.containers.container import Container
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


TEST_ITEMS = [

    pytest.mark.polarion('CMP-9948')(ContainersTestItem(Container, 'CMP-9948')),
    pytest.mark.polarion('CMP-10320')(ContainersTestItem(Template, 'CMP-10320')),
    pytest.mark.polarion('CMP-9992')(ContainersTestItem(ImageRegistry, 'CMP-9992')),
    pytest.mark.polarion('CMP-9981')(ContainersTestItem(Image, 'CMP-9981')),
    pytest.mark.polarion('CMP-9964')(ContainersTestItem(Node, 'CMP-9964')),
    pytest.mark.polarion('CMP-9932')(ContainersTestItem(Pod, 'CMP-9932')),
    pytest.mark.polarion('CMP-9870')(ContainersTestItem(Project, 'CMP-9870')),
    pytest.mark.polarion('CMP-9854')(ContainersTestItem(ContainersProvider, 'CMP-9854'))
]


def get_object_name(obj):
    return obj.__module__.title().split(".")[-1]


def set_random_tag(instance):
    navigate_to(instance, 'Details')
    toolbar.select('Policy', 'Edit Tags')

    # select random tag category
    cat_selector = AngularSelect("tag_cat")
    random_cat = random.choice(cat_selector.all_options)
    cat_selector.select_by_value(random_cat.value)

    # select random tag tag
    tag_selector = AngularSelect("tag_add")
    random_tag = random.choice([op for op in tag_selector.all_options if op.value != "select"])
    tag_selector.select_by_value(random_tag.value)

    # Save tag conig
    form_buttons.save()

    return Tag(display_name=random_tag.text, category=random_cat.text)


def wait_for_tag(obj_inst):
    # Waiting for some tag to appear at "My Company Tags" and return pop'ed last tag
    return wait_for(lambda: getattr(obj_inst.summary.smart_management,
                                    'my_company_tags', []), fail_condition=[],
                    num_sec=30, delay=5, fail_func=obj_inst.summary.reload).out.pop()


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
@pytest.mark.meta(blockers=[BZ(1479412,
                               forced_streams=['5.7'],
                               unblock=lambda test_item: test_item.obj != Container)])
def test_smart_management_add_tag(provider, test_item):

    # validate no tag set to project
    if test_item.obj is ContainersProvider:
        obj_inst = provider
    else:
        obj_inst = test_item.obj.get_random_instances(provider, count=1).pop()

    regex = r"([\w\s|\-|\*]+:([\w\s|\-|\*])+)|(No.*assigned)"
    try:
        # Remove all previous configured tags for given object
        obj_inst.remove_tags(obj_inst.get_tags())
    except RuntimeError:
        # Validate old tags formatting
        assert re.match(regex, wait_for_tag(obj_inst).text_value), \
            "Tag formatting is invalid! "

    # Config random tag for object\
    random_tag_setted = set_random_tag(obj_inst)

    # validate new tag format
    obj_inst.summary.reload()
    tag_display_text = wait_for_tag(obj_inst)
    tag_display_text = tag_display_text.text_value

    assert re.match(regex, tag_display_text), "Tag formatting is invalid! "
    actual_tags_on_instance = obj_inst.get_tags()

    # Validate tag seted successfully
    assert len(actual_tags_on_instance) == 1, "Fail to set a tag for {obj_type}".format(
        obj_type=get_object_name(test_item.obj))
    actual_tags_on_instance = actual_tags_on_instance.pop()

    # Validate tag value
    assert actual_tags_on_instance.display_name == random_tag_setted.display_name, \
        "Tag value not correctly configured"
