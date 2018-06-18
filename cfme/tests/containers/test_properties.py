# -*- coding: utf-8 -*-
import pytest

from wrapanapi.utils import eval_strings

from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.image import Image, ImageCollection
from cfme.containers.image_registry import (ImageRegistry,
                                            ImageRegistryCollection)
from cfme.containers.node import Node, NodeCollection
from cfme.containers.pod import Pod, PodCollection
from cfme.containers.project import Project, ProjectCollection
from cfme.containers.route import Route, RouteCollection
from cfme.containers.service import Service, ServiceCollection
from cfme.containers.template import Template, TemplateCollection
from cfme.containers.volume import Volume, VolumeCollection
from cfme.containers.container import Container, ContainerCollection

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.soft_get import soft_get


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9945')(
        ContainersTestItem(
            Container,
            'CMP-9945',
            expected_fields=[
                'Name', 'State', 'Last State', 'Restart count', 'Backing Ref (Container ID)',
                'Privileged'],
            collection_object=ContainerCollection
        )
    ),
    pytest.mark.polarion('CMP-10430')(
        ContainersTestItem(
            Project,
            'CMP-10430',
            expected_fields=['Name', 'Creation timestamp', 'Resource version'],
            collection_object=ProjectCollection
        )
    ),
    pytest.mark.polarion('CMP-9877')(
        ContainersTestItem(
            Route,
            'CMP-9877',
            expected_fields=['Name', 'Creation timestamp', 'Resource version', 'Host Name'],
            collection_object=RouteCollection
        )
    ),
    pytest.mark.polarion('CMP-9911')(
        ContainersTestItem(
            Pod,
            'CMP-9911',
            expected_fields=[
                'Name', 'Status', 'Creation timestamp', 'Resource version',
                'Restart policy', 'DNS Policy', 'IP Address'
            ],
            collection_object=PodCollection
        )
    ),
    pytest.mark.polarion('CMP-9960')(
        ContainersTestItem(
            Node,
            'CMP-9960',
            expected_fields=[
                'Name', 'Creation timestamp', 'Resource version', 'Number of CPU Cores',
                'Memory', 'Max Pods Capacity', 'System BIOS UUID', 'Machine ID',
                'Infrastructure Machine ID', 'Container runtime version',
                'Kubernetes kubelet version', 'Kubernetes proxy version',
                'Operating System Distribution', 'Kernel version',
            ],
            collection_object=NodeCollection
        )
    ),
    pytest.mark.polarion('CMP-9890')(
        ContainersTestItem(
            Service,
            'CMP-9890',
            expected_fields=[
                'Name', 'Creation timestamp', 'Resource version', 'Session affinity',
                'Type', 'Portal IP'
            ],
            collection_object=ServiceCollection
        )
    ),
    pytest.mark.polarion('CMP-9988')(
        ContainersTestItem(
            ImageRegistry,
            'CMP-9988',
            expected_fields=['Host'],
            collection_object=ImageRegistryCollection
        )
    ),
    pytest.mark.polarion('CMP-10316')(
        ContainersTestItem(
            Template,
            'CMP-10316',
            expected_fields=['Name', 'Creation timestamp', 'Resource version'],
            collection_object=TemplateCollection
        )
    ),
    pytest.mark.polarion('CMP-10407')(
        ContainersTestItem(
            Volume,
            'CMP-10407',
            expected_fields=[
                'Name',
                'Creation timestamp', 'Resource version', 'Access modes', 'Reclaim policy',
                'Status phase', 'Volume path'],
            collection_object=VolumeCollection
        )
    ),
    pytest.mark.polarion('CMP-9978')(
        ContainersTestItem(
            Image,
            'CMP-9978',
            expected_fields=[
                'Name', 'Image Id', 'Full Name', 'Architecture', 'Author',
                'Command', 'Entrypoint', 'Docker Version', 'Exposed Ports', 'Size'
            ],
            collection_object=ImageCollection
        )
    )
]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_properties(provider, appliance, test_item, soft_assert):

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
