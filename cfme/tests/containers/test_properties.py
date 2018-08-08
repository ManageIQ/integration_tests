# -*- coding: utf-8 -*-
import pytest
from wrapanapi.utils import eval_strings

from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.route import Route, RouteCollection
from cfme.containers.project import Project, ProjectCollection
from cfme.containers.service import Service, ServiceCollection
from cfme.containers.node import Node, NodeCollection
from cfme.containers.image import Image, ImageCollection
from cfme.containers.image_registry import (ImageRegistry,
                                            ImageRegistryCollection)
from cfme.containers.pod import Pod, PodCollection
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


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9945')(
        ContainersTestItem(
            Container,
            'CMP-9945',
            expected_fields=[
                'name', 'state', 'last state', 'restart count',
                'backing ref (container id)', 'privileged'
            ],
            collection_object=ContainerCollection
        )
    ),
    pytest.mark.polarion('CMP-10430')(
        ContainersTestItem(
            Project,
            'CMP-10430',
            expected_fields=['name', 'creation timestamp', 'resource version'],
            collection_object=ProjectCollection
        )
    ),
    pytest.mark.polarion('CMP-9877')(
        ContainersTestItem(
            Route,
            'CMP-9877',
            expected_fields=['name', 'creation timestamp', 'resource version', 'host name'],
            collection_object=RouteCollection
        )
    ),
    pytest.mark.polarion('CMP-9911')(
        ContainersTestItem(
            Pod,
            'CMP-9911',
            expected_fields=[
                'name', 'creation timestamp', 'resource version',
                'restart policy', 'dns policy', 'ip address'
            ],
            collection_object=PodCollection
        )
    ),
    pytest.mark.polarion('CMP-9960')(
        ContainersTestItem(
            Node,
            'CMP-9960',
            expected_fields=[
                'name', 'creation timestamp', 'resource version', 'number of cpu cores',
                'memory', 'max pods capacity', 'system bios uuid', 'machine id',
                'infrastructure machine id', 'runtime version', 'kubelet version',
                'proxy version', 'operating system distribution', 'kernel version',
            ],
            collection_object=NodeCollection
        )
    ),
    pytest.mark.polarion('CMP-9978')(
        ContainersTestItem(
            Image,
            'CMP-9978',
            expected_fields=[
                'name', 'image id', 'full name', 'architecture', 'author',
                'entrypoint', 'docker version', 'exposed ports', 'size'
            ],
            collection_object=ImageCollection
        )
    ),
    pytest.mark.polarion('CMP-9890')(
        ContainersTestItem(
            Service,
            'CMP-9890',
            expected_fields=[
                'name', 'creation timestamp', 'resource version', 'session affinity',
                'type', 'portal ip'
            ],
            collection_object=ServiceCollection
        )
    ),
    pytest.mark.polarion('CMP-9988')(
        ContainersTestItem(
            ImageRegistry,
            'CMP-9988',
            expected_fields=['host'],
            collection_object=ImageRegistryCollection
        )
    ),
    pytest.mark.polarion('CMP-10316')(
        ContainersTestItem(
            Template,
            'CMP-10316',
            expected_fields=['name', 'creation timestamp', 'resource version'],
            collection_object=TemplateCollection
        )
    ),
    pytest.mark.polarion('CMP-10407')(
        ContainersTestItem(Volume,
            'CMP-10407',
            expected_fields=[
                'name',
                'creation timestamp',
                'resource version',
                'access modes',
                'reclaim policy',
                'status phase',
                'nfs server',
                'volume path'],
            collection_object=VolumeCollection
        )
    )
]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_properties(provider, appliance, test_item, soft_assert):

    instances = test_item.collection_object(appliance).get_random_instances(count=2)

    for instance in instances:

        expected_fields = test_item.expected_fields
        for field in expected_fields:
            view = navigate_to(instance, 'Details')
            try:
                soft_get(view.entities.properties.read(), field, dict_=True)
            except AttributeError:
                soft_assert(False, '{} "{}" properties table has missing field - "{}"'
                                   .format(test_item.obj.__name__, instance.name, field))


def test_pods_conditions(provider, appliance, soft_assert):

    selected_pods_cfme = {pd.name: pd
                          for pd in PodCollection(appliance).get_random_instances(count=3)}

    pods_per_ready_status = provider.pods_per_ready_status()
    for pod_name in selected_pods_cfme:
        cfme_pod = selected_pods_cfme[pod_name]
        view = navigate_to(cfme_pod, 'Details')
        ose_pod_condition = pods_per_ready_status[pod_name]
        cfme_pod_condition = {r.name.text: eval_strings([r.status.text]).pop()
                              for r in view.entities.conditions.rows()}

        for status in cfme_pod_condition:
            soft_assert(ose_pod_condition[status] == cfme_pod_condition[status],
                        'The Pod {} status mismatch: It is "{}" in openshift while cfme sees "{}".'
                        .format(status, cfme_pod.name, ose_pod_condition[status],
                                cfme_pod_condition[status]))
