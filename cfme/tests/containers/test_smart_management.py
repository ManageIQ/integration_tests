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
import random

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


TEST_ITEMS = [
    pytest.mark.polarion('CMP-10320')(
        ContainersTestItem(Template, 'CMP-10320')
    ),
    pytest.mark.polarion('CMP-9992')(
        ContainersTestItem(ImageRegistry, 'CMP-9992')
    ),
    pytest.mark.polarion('CMP-9981')(
        ContainersTestItem(Image, 'CMP-9981')
    ),
    pytest.mark.polarion('CMP-9964')(
        ContainersTestItem(Node, 'CMP-9964')
    ),
    pytest.mark.polarion('CMP-9932')(
        ContainersTestItem(Pod, 'CMP-9932')
    ),
    pytest.mark.polarion('CMP-9870')(
        ContainersTestItem(Project, 'CMP-9870')
    ),
    pytest.mark.polarion('CMP-9854')(
        ContainersTestItem(ContainersProvider, 'CMP-9854')
    )
]


def set_random_tag(instance):
    navigate_to(instance, 'Details')
    toolbar.select('Policy', 'Edit Tags')

    # select random tag category
    cat_selector = AngularSelect("tag_cat")
    random_cat = random.choice(cat_selector.all_options).text
    cat_selector.select_by_visible_text(random_cat)

    # select random tag tag
    tag_selector = AngularSelect("tag_add")
    random_tag = random.choice(tag_selector.all_options).text
    tag_selector.select_by_visible_text(random_tag)

    # Save tog configuration
    form_buttons.save()

    return Tag(display_name=random_tag, category=random_cat)


@pytest.mark.parametrize('test_item',
                         TEST_ITEMS, ids=[testItem.args[1].pretty_id() for testItem in TEST_ITEMS])
def test_smart_management_add_tag(provider, test_item):

    # Select random project
    navigate_to(test_item.obj, 'All')
    chosen_row = random.choice(paged_tbl.rows_as_list())

    # validate no tag set to project
    obj_inst = test_item.obj(chosen_row.name.text, provider)

    # Remove all previous configured tags for given object
    obj_inst.remove_tags(obj_inst.get_tags())

    # Config random tag for object
    random_sag_setted = set_random_tag(obj_inst)
    actual_tags_on_instance = obj_inst.get_tags().pop()

    # Validate tag configuration
    assert actual_tags_on_instance.display_name == random_sag_setted.display_name, \
        "Display name not correctly configured"
