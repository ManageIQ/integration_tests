import pytest

from cfme import test_requirements
from cfme.containers.container import Container
from cfme.containers.container import ContainerCollection
from cfme.containers.image import Image
from cfme.containers.image import ImageCollection
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.image_registry import ImageRegistryCollection
from cfme.containers.node import Node
from cfme.containers.node import NodeCollection
from cfme.containers.pod import Pod
from cfme.containers.pod import PodCollection
from cfme.containers.project import Project
from cfme.containers.project import ProjectCollection
from cfme.containers.provider import ContainersProvider
from cfme.containers.provider import ContainersTestItem
from cfme.containers.replicator import Replicator
from cfme.containers.replicator import ReplicatorCollection
from cfme.containers.service import Service
from cfme.containers.service import ServiceCollection
from cfme.containers.template import Template
from cfme.containers.template import TemplateCollection
from cfme.containers.volume import Volume
from cfme.containers.volume import VolumeCollection
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module'),
    test_requirements.containers
]

TEST_ITEMS = [
    ContainersTestItem(ContainersProvider, 'container_provider_relationships', collection_obj=None),
    ContainersTestItem(Container, 'container_relationships', collection_obj=ContainerCollection),
    ContainersTestItem(Pod, 'pod_relationships', collection_obj=PodCollection),
    ContainersTestItem(Service, 'service_relationships', collection_obj=ServiceCollection),
    ContainersTestItem(Node, 'node_relationships', collection_obj=NodeCollection),
    ContainersTestItem(Replicator, 'replicator_relationships', collection_obj=ReplicatorCollection),
    ContainersTestItem(Image, 'image_relationships', collection_obj=ImageCollection),
    ContainersTestItem(ImageRegistry, 'image_registry_relationships',
                       collection_obj=ImageRegistryCollection),
    ContainersTestItem(Project, 'project_relationships', collection_obj=ProjectCollection),
    ContainersTestItem(Template, 'template_relationships', collection_obj=TemplateCollection),
    ContainersTestItem(Volume, 'volume_relationships', collection_obj=VolumeCollection)]


@pytest.mark.parametrize('test_item', TEST_ITEMS, scope='module',
                         ids=[ti.pretty_id() for ti in TEST_ITEMS])
@pytest.mark.usefixtures('has_persistent_volume')
@pytest.mark.usefixtures('setup_provider_modscope')
def test_relationships_tables(soft_assert, provider, has_persistent_volume, appliance, test_item):
    """This test verifies the integrity of the Relationships table.
    clicking on each field in the Relationships table takes the user
    to either Summary page where we verify that the field that appears
    in the Relationships table also appears in the Properties table,
    or to the page where the number of rows is equal to the number
    that is displayed in the Relationships table.

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
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
