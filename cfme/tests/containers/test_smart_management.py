import pytest
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from cfme.web_ui import toolbar, AngularSelect, form_buttons
from cfme.configure.configuration import Tag
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.image import Image
from cfme.containers.project import Project, paged_tbl
from cfme.containers.node import Node
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.template import Template
from cfme.containers.provider import navigate_and_get_rows
import random

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


TEST_ITEMS = [
    #pytest.mark.polarion('CMP-10320')(ContainersTestItem(Template, 'CMP-10320')),
    #pytest.mark.polarion('CMP-9992')(ContainersTestItem(ImageRegistry,'CMP-9992')),
    pytest.mark.polarion('CMP-9981')(ContainersTestItem(Image, 'CMP-9981'))#,
    #pytest.mark.polarion('CMP-9964')(ContainersTestItem(Node, 'CMP-9964')),
    #pytest.mark.polarion('CMP-9932')(ContainersTestItem(Pod,'CMP-9932')),
    #pytest.mark.polarion('CMP-9870')(ContainersTestItem(Project, 'CMP-9870')),
    #pytest.mark.polarion('CMP-9854')(ContainersTestItem(ContainersProvider, 'CMP-9854'))
]


def set_random_tag(instance):
    navigate_to(instance, 'Details')
    toolbar.select('Policy', 'Edit Tags')

    # select random tag category
    cat_selector = AngularSelect("tag_cat")
    random_cat = random.choice(cat_selector.all_options)
    print "Random cat: {cat}".format(cat=random_cat.text)
    cat_selector.select_by_value(random_cat.value)

    # select random tag tag
    tag_selector = AngularSelect("tag_add")
    random_tag = random.choice(filter(lambda op: op.value != "select", tag_selector.all_options))
    print "Random tag: {tag}".format(tag=random_tag)
    tag_selector.select_by_value(random_tag.value)

    # Save tag conig
    form_buttons.save()

    return Tag(display_name=random_tag.text, category=random_cat.text)

def objFactory(Type, row, provider):

    factory = {"Provider": {"name": row.name.text},
               "Project": {"name": row.name.text, "provider": provider},
               "Pod": {"name": row.name.text, "provider": provider},
               "Node": {"name": row.name.text, "provider": provider},
               "Template": {"name": row.name.text, "provider": provider},
               "Image": {"name": row.name.text, "provider": provider, "tag": row.tag},
               "Image_Registry": {"host": row.name.text, "provider": provider}}
    return Type(**factory[Type.__module__.title().split(".")[-1]])


@pytest.mark.parametrize('test_item',
                         TEST_ITEMS, ids=[testItem.args[1].pretty_id() for testItem in TEST_ITEMS])
def test_smart_management_add_tag(provider, test_item):


    # Select random project
    #navigate_to(test_item.obj, 'All')
    #toolbar.select('List View')
    #chosen_row = random.choice(paged_tbl.rows_as_list())

    chosen_row = navigate_and_get_rows(provider, test_item.obj, 1).pop()

    # validate no tag set to project
    obj_inst = objFactory(test_item.obj, chosen_row, provider)
    print "Chosen instance, {inst}".format(inst=chosen_row.name.text)
    # Remove all previous configured tags for given object

    all_instance_tags = obj_inst.get_tags()
    obj_inst.remove_tags(all_instance_tags)

    # Config random tag for object
    random_tag_setted = set_random_tag(obj_inst)
    actual_tags_on_instance = obj_inst.get_tags()

    # Validate tag seted successfully
    assert len(actual_tags_on_instance) == 1, \
        "Fail to set a tag for {type}".format(type=test_item.obj.__module__.title().split(".")[-1])
    actual_tags_on_instance = actual_tags_on_instance.pop()

    # Validate tag value
    assert actual_tags_on_instance.display_name == random_tag_setted.display_name, \
        "Display name not correctly configured"
