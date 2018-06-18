import pytest

from cfme.containers.container import Container, ContainerCollection
from cfme.containers.image import Image, ImageCollection
from cfme.containers.image_registry import ImageRegistry, ImageRegistryCollection
from cfme.containers.node import Node, NodeCollection
from cfme.containers.pod import Pod, PodCollection
from cfme.containers.project import Project, ProjectCollection
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.replicator import Replicator, ReplicatorCollection
from cfme.containers.service import Service, ServiceCollection
from cfme.containers.template import Template, TemplateCollection
from cfme.containers.volume import Volume, VolumeCollection
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module')
]

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
    pytest.mark.polarion('CMP-9868')(ContainersTestItem(
        Project, 'CMP-9868', collection_obj=ProjectCollection)),
    pytest.mark.polarion('CMP-10319')(ContainersTestItem(
        Template, 'CMP-10319', collection_obj=TemplateCollection)),
    pytest.mark.polarion('CMP-10410')(ContainersTestItem(
        Volume, 'CMP-10410', collection_obj=VolumeCollection))
]


@pytest.mark.parametrize('test_item', TEST_ITEMS, scope='module',
                         ids=[ti.args[1].pretty_id() for ti in TEST_ITEMS])
@pytest.mark.usefixtures('has_persistent_volume')
@pytest.mark.usefixtures('setup_provider_modscope')
def test_relationships_tables(soft_assert, provider, has_persistent_volume, appliance, test_item):
    """This test verifies the integrity of the Relationships table.
    clicking on each field in the Relationships table takes the user
    to either Summary page where we verify that the field that appears
    in the Relationships table also appears in the Properties table,
    or to the page where the number of rows is equal to the number
    that is displayed in the Relationships table.
    """
    instances = ([provider] if test_item.obj is ContainersProvider
                 else test_item.collection_obj(appliance).all())
    for instance in instances:
        if instance.exists:
            test_obj = instance
            break
    else:
        pytest.skip("No content found for test")
    # Check the relationships linking & data integrity
    view = navigate_to(test_obj, 'Details')
    relationships_rows = view.entities.summary("Relationships").fields
    for row_entry in relationships_rows:
        text_of_field = view.entities.summary("Relationships").get_text_of(row_entry)
        if text_of_field == '0':
            continue
        view.entities.summary('Relationships').click_at(row_entry)
        if text_of_field.isdigit():
            new_view = appliance.browser.create_view(test_item.obj.all_view)
            value = int(text_of_field)
            items_amount = int(new_view.paginator.items_amount)
            soft_assert(items_amount == value, (
                'Mismatch between relationships table value and item amount in the object table: '
                'field: {}; relationships_table: {}; object table: {};'
                .format(text_of_field, value, instance.name, items_amount))
            )
        else:
            new_view = appliance.browser.create_view(test_item.obj.details_view)
            assert text_of_field in new_view.breadcrumb.active_location
        view = navigate_to(test_obj, 'Details')


@pytest.mark.polarion('CMP-9934')
@pytest.mark.usefixtures('setup_provider')
def test_container_status_relationships_data_integrity(provider, appliance, soft_assert):
    """ This test verifies that the sum of running, waiting and terminated containers
        in the status summary table
        is the same number that appears in the Relationships table containers field
    """

    pod_instances = PodCollection(appliance).all()
    for pod_instance in pod_instances:
        if not pod_instance.exists:
            continue
        view = navigate_to(pod_instance, 'Details')

        summary_fields = view.entities.summary('Container Statuses Summary').fields

        soft_assert(
            int(view.entities.summary('Relationships').get_text_of('Containers')) ==
            sum([int(view.entities.summary('Container Statuses Summary').get_text_of(field))
                 for field in summary_fields]))
