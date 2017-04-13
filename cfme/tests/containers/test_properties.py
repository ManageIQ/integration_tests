# -*- coding: utf-8 -*-
import pytest

from cfme.containers.provider import ContainersProvider, navigate_and_get_rows,\
    ContainersTestItem
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.service import Service
from cfme.containers.container import Container
from cfme.containers.node import Node
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.template import Template
from cfme.containers.volume import Volume

from utils import testgen, version
from utils.version import current_version
from utils.soft_get import soft_get
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9945')(
        ContainersTestItem(
            Container,
            'CMP-9945',
            expected_fields=[
                'name', 'state', 'last_state', 'restart_count',
                'backing_ref_container_id', 'privileged', 'selinux_level'
            ]
        )
    ),
    pytest.mark.polarion('CMP-10430')(
        ContainersTestItem(
            Project,
            'CMP-10430',
            expected_fields=['name', 'creation_timestamp', 'resource_version']
        )
    ),
    pytest.mark.polarion('CMP-9877')(
        ContainersTestItem(
            Route,
            'CMP-9877',
            expected_fields=['name', 'creation_timestamp', 'resource_version', 'host_name']
        )
    ),
    pytest.mark.polarion('CMP-9911')(
        ContainersTestItem(
            Pod,
            'CMP-9911',
            expected_fields=[
                'name', 'phase', 'creation_timestamp', 'resource_version',
                'restart_policy', 'dns_policy', 'ip_address'
            ]
        )
    ),
    pytest.mark.polarion('CMP-9960')(
        ContainersTestItem(
            Node,
            'CMP-9960',
            expected_fields=[
                'name', 'creation_timestamp', 'resource_version', 'number_of_cpu_cores',
                'memory', 'max_pods_capacity', 'system_bios_uuid', 'machine_id',
                'infrastructure_machine_id', 'runtime_version', 'kubelet_version',
                'proxy_version', 'operating_system_distribution', 'kernel_version',
            ]
        )
    ),
    pytest.mark.polarion('CMP-9978')(
        ContainersTestItem(
            Image,
            'CMP-9978',
            expected_fields={
                version.LOWEST: ['name', 'tag', 'image_id', 'full_name'],
                '5.7': [
                    'name', 'tag', 'image_id', 'full_name', 'architecture', 'author',
                    'entrypoint', 'docker_version', 'exposed_ports', 'size'
                ]
            }
        )
    ),
    pytest.mark.polarion('CMP-9890')(
        ContainersTestItem(
            Service,
            'CMP-9890',
            expected_fields=[
                'name', 'creation_timestamp', 'resource_version', 'session_affinity',
                'type', 'portal_ip'
            ]
        )
    ),
    pytest.mark.polarion('CMP-9988')(
        ContainersTestItem(
            ImageRegistry,
            'CMP-9988',
            expected_fields=['host']
        )
    ),
    pytest.mark.polarion('CMP-10316')(
        ContainersTestItem(
            Template,
            'CMP-10316',
            expected_fields=['name', 'creation_timestamp', 'resource_version']
        )
    ),
    pytest.mark.polarion('CMP-10407')(
        ContainersTestItem(Volume,
            'CMP-10407',
            expected_fields=[
                'name',
                'creation_timestamp',
                'resource_version',
                'access_modes',
                'reclaim_policy',
                'status_phase',
                'nfs_server',
                'volume_path']
        )
    )
]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ti.args[1].pretty_id() for ti in TEST_ITEMS])
def test_properties(provider, test_item, soft_assert):

    if current_version() < "5.7" and test_item.obj == Template:
        pytest.skip('Templates are not exist in CFME version lower than 5.7. skipping...')

    rows = navigate_and_get_rows(provider, test_item.obj, 2)

    if not rows:
        pytest.skip('No records found for {}s. Skipping...'.format(test_item.obj.__name__))
    names = [r[2].text for r in rows]

    if test_item.obj is Container:
        args = [(r.pod_name.text, ) for r in rows]
    elif test_item.obj is Image:
        args = [(r.tag.text, provider) for r in rows]
    else:
        args = [(provider, ) for _ in rows]

    for name, arg in zip(names, args):

        instance = test_item.obj(name, *arg)
        navigate_to(instance, 'Details')
        if isinstance(test_item.expected_fields, dict):
            expected_fields = version.pick(test_item.expected_fields)
        else:
            expected_fields = test_item.expected_fields
        for field in expected_fields:
            try:
                soft_get(instance.summary.properties, field)
            except AttributeError:
                soft_assert(False, '{} "{}" properties table has missing field - "{}"'
                                   .format(test_item.obj.__name__, name, field))
