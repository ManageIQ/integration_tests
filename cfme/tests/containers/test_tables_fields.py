import pytest

from cfme import test_requirements
from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import Node
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider
from cfme.containers.provider import ContainersTestItem
from cfme.containers.replicator import Replicator
from cfme.containers.route import Route
from cfme.containers.service import Service
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]


TEST_ITEMS = [
    ContainersTestItem(
        ContainersProvider, 'container_provider_table_fields',
        fields_to_verify=['hostname', 'port', 'type'],
        collection_name=None),
    ContainersTestItem(
        Route, 'route__table_fields',
        fields_to_verify=['provider', 'project_name'],
        collection_name='container_routes'),
    ContainersTestItem(
        Container, 'container__table_fields',
        fields_to_verify=['pod_name', 'image', 'state'],
        collection_name='containers'),
    ContainersTestItem(
        Pod, 'pod__table_fields',
        fields_to_verify=['provider', 'project_name', 'ready', 'containers', 'phase',
                          'restart_policy', 'dns_policy'],
        collection_name='container_pods'),
    ContainersTestItem(
        Service, 'service_table_fields9',
        fields_to_verify=['provider', 'project_name', 'type', 'portal_ip', 'session_affinity',
                          'pods'],
        collection_name='container_services'),
    ContainersTestItem(
        Node, 'node_table_fields',
        fields_to_verify=['provider', 'ready', 'operating_system', 'kernel_version',
                          'runtime_version'],
        collection_name='container_nodes'),
    ContainersTestItem(
        Replicator, 'replicator_table_fields',
        fields_to_verify=['provider', 'project_name', 'replicas', 'current_replicas'],
        collection_name='container_replicators'),
    ContainersTestItem(
        Image, 'image_table_fields',
        fields_to_verify=['provider', 'tag', 'id', 'image_registry'],
        collection_name='container_images'),
    ContainersTestItem(
        ImageRegistry, 'image_registry_table_fields',
        fields_to_verify=['port', 'provider'],
        collection_name='container_image_registries'),
    ContainersTestItem(
        Project, 'project_table_fields',
        fields_to_verify=['provider', 'container_routes', 'container_services',
                          'container_replicators', 'pods', 'containers', 'images'],
        collection_name='container_projects')]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ti.pretty_id() for ti in TEST_ITEMS])
def test_tables_fields(provider, test_item, soft_assert, appliance):

    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    view = navigate_to((test_item.obj if test_item.obj is ContainersProvider
                        else getattr(appliance.collections, test_item.collection_name)), 'All')
    view.toolbar.view_selector.select('List View')
    for row in view.entities.elements.rows():
        name_field = getattr(row, 'name', getattr(row, 'host', None))
        name = name_field.text
        for field in test_item.fields_to_verify:

            try:
                value = getattr(row, field)
            except AttributeError:
                soft_assert(False, '{}\'s list table: field  not exist: {}'
                            .format(test_item.obj.__name__, field))
                continue

            soft_assert(value, '{}\'s list table: {} row - has empty field: {}'
                        .format(test_item.obj.__name__, name, field))


def test_containers_details_view_title(appliance):
    """
    The word summery has to apper as part of the container title
    In this test the detail container view is tested
    Test based on BZ1338801

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    random_container = appliance.collections.containers.all().pop()
    view = navigate_to(random_container, "Details")
    assert "Summary" in view.title.text, (
        "The word \"Summary\" is missing in container details view")
