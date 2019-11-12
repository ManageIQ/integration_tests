import pytest
from wrapanapi.utils import eval_strings

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
from cfme.containers.route import Route
from cfme.containers.route import RouteCollection
from cfme.containers.service import Service
from cfme.containers.service import ServiceCollection
from cfme.containers.template import Template
from cfme.containers.template import TemplateCollection
from cfme.containers.volume import Volume
from cfme.containers.volume import VolumeCollection
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]


TEST_ITEMS = [
    ContainersTestItem(
        Container, 'test_properties_container_provider',
        expected_fields=[
            'Name', 'State', 'Last State', 'Restart count', 'Backing Ref (Container ID)'],
        collection_object=ContainerCollection),
    ContainersTestItem(
        Project, 'test_properties_container_project',
        expected_fields=['Name', 'Creation timestamp', 'Resource version'],
        collection_object=ProjectCollection),
    ContainersTestItem(
        Route, 'test_properties_container_route',
        expected_fields=['Name', 'Creation timestamp', 'Resource version', 'Host Name'],
        collection_object=RouteCollection),
    ContainersTestItem(
        Pod, 'test_properties_container_pod',
        expected_fields=[
            'Name', 'Status', 'Creation timestamp', 'Resource version',
            'Restart policy', 'DNS Policy', 'IP Address'],
        collection_object=PodCollection),
    ContainersTestItem(
        Node, 'test_properties_container_node',
        expected_fields=[
            'Name', 'Creation timestamp', 'Resource version', 'Number of CPU Cores',
            'Memory', 'Max Pods Capacity', 'System BIOS UUID', 'Machine ID',
            'Infrastructure Machine ID', 'Container runtime version',
            'Kubernetes kubelet version', 'Kubernetes proxy version',
            'Operating System Distribution', 'Kernel version'],
        collection_object=NodeCollection),
    ContainersTestItem(
        Service, 'test_properties_container_service',
        expected_fields=[
            'Name', 'Creation timestamp', 'Resource version', 'Session affinity',
            'Type', 'Portal IP'],
        collection_object=ServiceCollection),
    ContainersTestItem(
        ImageRegistry, 'test_properties_container_image_registry',
        expected_fields=['Host'],
        collection_object=ImageRegistryCollection),
    ContainersTestItem(
        Template, 'test_properties_container_template',
        expected_fields=['Name', 'Creation timestamp', 'Resource version'],
        collection_object=TemplateCollection),
    ContainersTestItem(
        Volume, 'test_properties_container_volumes',
        expected_fields=[
            'Name',
            'Creation timestamp', 'Resource version', 'Access modes', 'Reclaim policy',
            'Status phase', 'Volume path'],
        collection_object=VolumeCollection),
    ContainersTestItem(
        Image, 'test_properties_container_image',
        expected_fields=[
            'Name', 'Image Id', 'Full Name', 'Architecture', 'Author',
            'Command', 'Entrypoint', 'Docker Version', 'Exposed Ports', 'Size'],
        collection_object=ImageCollection)]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_properties(provider, appliance, test_item, soft_assert):

    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    instances = test_item.collection_object(appliance).all()
    for inst in instances:
        if inst.exists:
            instance = inst
            break
    else:
        pytest.skip("No content found for test")

    expected_fields = test_item.expected_fields

    view = navigate_to(instance, 'Details')

    for field in expected_fields:
        try:
            view.entities.summary('Properties').get_field(field)
        except NameError:
            soft_assert(False, '{} "{}" properties table has missing field - "{}"'
                               .format(test_item.obj.__name__, instance.name, field))


def test_pods_conditions(provider, appliance, soft_assert):

    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    selected_pods_cfme = appliance.collections.container_pods.all()

    pods_per_ready_status = provider.pods_per_ready_status()
    for pod in selected_pods_cfme:
        if not pod.exists:
            continue
        view = navigate_to(pod, 'Details')
        ose_pod_condition = pods_per_ready_status[pod.name]
        cfme_pod_condition = {r.name.text: eval_strings([r.status.text]).pop()
                              for r in view.entities.conditions.rows()}

        for status in cfme_pod_condition:
            # If any pods are in a False state, the condition will be reported as False
            soft_assert(all(cond for cond in ose_pod_condition) == cfme_pod_condition['Ready'],
                        'The Pod {} status mismatch: It is "{}" in openshift while cfme sees "{}".'
                        .format(status, pod.name, ose_pod_condition,
                                cfme_pod_condition['Ready']))
