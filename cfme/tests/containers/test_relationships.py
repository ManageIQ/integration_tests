from random import randrange

import pytest

from cfme.containers.pod import Pod
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.service import Service
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.template import Template
from cfme.containers.container import Container
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.volume import Volume
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module')
]


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9851')(ContainersTestItem(ContainersProvider, 'CMP-9851')),
    pytest.mark.polarion('CMP-9947')(ContainersTestItem(Container, 'CMP-9947')),
    pytest.mark.polarion('CMP-9929')(ContainersTestItem(Pod, 'CMP-9929')),
    pytest.mark.polarion('CMP-10564')(ContainersTestItem(Service, 'CMP-10564')),
    # TODO Add Node back into the list when other classes are updated to use WT views and widgets.
    # pytest.mark.polarion('CMP-9962')(ContainersTestItem(Node, 'CMP-9962')),
    pytest.mark.polarion('CMP-10565')(ContainersTestItem(Replicator, 'CMP-10565')),
    pytest.mark.polarion('CMP-9980')(ContainersTestItem(Image, 'CMP-9980')),
    pytest.mark.polarion('CMP-9994')(ContainersTestItem(ImageRegistry, 'CMP-9994')),
    pytest.mark.polarion('CMP-9868')(ContainersTestItem(Project, 'CMP-9868')),
    pytest.mark.polarion('CMP-10319')(ContainersTestItem(Template, 'CMP-10319')),
    pytest.mark.polarion('CMP-10410')(ContainersTestItem(Volume, 'CMP-10410'))
]


@pytest.mark.parametrize('test_item', TEST_ITEMS, scope='module',
                         ids=[ti.args[1].pretty_id() for ti in TEST_ITEMS])
@pytest.mark.usefixtures('has_persistent_volume')
@pytest.mark.usefixtures('setup_provider_modscope')
def test_relationships_tables(provider, has_persistent_volume, appliance, test_item):
    """This test verifies the integrity of the Relationships table.
    clicking on each field in the Relationships table takes the user
    to either Summary page where we verify that the field that appears
    in the Relationships table also appears in the Properties table,
    or to the page where the number of rows is equal to the number
    that is displayed in the Relationships table.
    """
    instance = (provider if test_item.obj is ContainersProvider
                else test_item.obj.get_random_instances(provider, 1, appliance).pop())
    # Check the relationships linking & data integrity
    view = navigate_to(instance, 'Details')
    relations = [key for key, val in view.entities.relationships.read().items() if val != '0']
    relation = relations[randrange(len(relations))]
    field = view.entities.relationships.get_field(relation)[1]
    text = field.text
    field.click()
    if text.isdigit():
        view = appliance.browser.create_view(test_item.obj.all_view)
        value = int(text)
        items_amount = int(view.paginator.items_amount)
        assert items_amount == value, (
            'Difference between the value({}) in the relationships table in {}'
            'to number of records ({}) in the target page'
            .format(value, instance.name, items_amount)
        )
    else:
        view = appliance.browser.create_view(test_item.obj.details_view)
        assert view.title.text == '{} (Summary)'.format(text)


@pytest.mark.polarion('CMP-9934')
@pytest.mark.usefixtures('setup_provider')
def test_container_status_relationships_data_integrity(provider, appliance, soft_assert):
    """ This test verifies that the sum of running, waiting and terminated containers
        in the status summary table
        is the same number that appears in the Relationships table containers field
    """
    for obj in Pod.get_random_instances(provider, count=3, appliance=appliance):
        view = navigate_to(obj, 'Details')
        soft_assert(
            (int(view.entities.relationships.read()['Containers']) ==
             sum([int(v) for v in view.entities.container_statuses_summary.read().values()]))
        )
