from random import randrange

import pytest

from cfme.containers.pod import Pod, PodCollection
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.service import Service, ServiceCollection
from cfme.containers.replicator import Replicator, ReplicatorCollection
from cfme.containers.image import Image, ImageCollection
from cfme.containers.template import Template, TemplateCollection
from cfme.containers.container import Container, ContainerCollection
from cfme.containers.image_registry import ImageRegistry, ImageRegistryCollection
from cfme.containers.node import Node, NodeCollection
from cfme.containers.volume import Volume, VolumeCollection
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module')
]


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9851')(ContainersTestItem(
        ContainersProvider, 'CMP-9851', collection_obj=None)),
    pytest.mark.polarion('CMP-9947')(ContainersTestItem(
        Container, 'CMP-9947', collection_obj=ContainerCollection)),
    pytest.mark.polarion('CMP-9929')(ContainersTestItem(
        Pod, 'CMP-9929', collection_obj=PodCollection)),
    pytest.mark.polarion('CMP-10564')(ContainersTestItem(
        Service, 'CMP-10564', collection_obj=ServiceCollection)),
    pytest.mark.polarion('CMP-9962')(ContainersTestItem(
        Node, 'CMP-9962', collection_obj=NodeCollection)),
    pytest.mark.polarion('CMP-10565')(ContainersTestItem(
        Replicator, 'CMP-10565', collection_obj=ReplicatorCollection)),
    pytest.mark.polarion('CMP-9980')(ContainersTestItem(
        Image, 'CMP-9980', collection_obj=ImageCollection)),
    pytest.mark.polarion('CMP-9994')(ContainersTestItem(
        ImageRegistry, 'CMP-9994', collection_obj=ImageRegistryCollection)),
    # https://bugzilla.redhat.com/show_bug.cgi?id=1530610
    # from cfme.containers.project import Project, ProjectCollection
    # pytest.mark.polarion('CMP-9868')(ContainersTestItem(
    #     Project, 'CMP-9868', collection_obj=ProjectCollection)),
    pytest.mark.polarion('CMP-10319')(ContainersTestItem(
        Template, 'CMP-10319', collection_obj=TemplateCollection)),
    pytest.mark.polarion('CMP-10410')(ContainersTestItem(
        Volume, 'CMP-10410', collection_obj=VolumeCollection))
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
                else test_item.collection_obj(appliance).get_random_instances().pop())
    # Check the relationships linking & data integrity
    view = navigate_to(instance, 'Details')
    relations = [key for key, val in view.entities.relationships.read().items() if val != '0']
    if appliance.version.is_in_series([5, 8]):  # Treat BZ#1518862
        relations = filter(lambda rel: rel != 'Containers', relations)
    relation = relations[randrange(len(relations))]
    field = view.entities.relationships.get_field(relation)[1]
    text = field.text
    field.click()
    if text.isdigit():
        view = appliance.browser.create_view(test_item.obj.all_view)
        value = int(text)
        items_amount = int(view.paginator.items_amount)
        assert items_amount == value, (
            'Mismatch between relationships table value and item amount in the object table: '
            'field: {}; relationships_table: {}; object table: {};'
            .format(field, value, instance.name, items_amount)
        )
    else:
        view = appliance.browser.create_view(test_item.obj.details_view)
        assert text in view.breadcrumb.active_location


@pytest.mark.polarion('CMP-9934')
@pytest.mark.usefixtures('setup_provider')
def test_container_status_relationships_data_integrity(provider, appliance, soft_assert):
    """ This test verifies that the sum of running, waiting and terminated containers
        in the status summary table
        is the same number that appears in the Relationships table containers field
    """
    for obj in PodCollection(appliance).get_random_instances(count=3):
        view = navigate_to(obj, 'Details')
        soft_assert(
            (int(view.entities.relationships.read()['Containers']) ==
             sum([int(v) for v in view.entities.container_statuses_summary.read().values()]))
        )
