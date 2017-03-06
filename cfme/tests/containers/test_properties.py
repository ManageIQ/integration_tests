# -*- coding: utf-8 -*-
import pytest

from cfme.containers.provider import ContainersProvider, navigate_and_get_rows
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.service import Service
from cfme.containers.container import Container
from cfme.containers.node import Node
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.template import Template

from utils import testgen, version
from utils.version import current_version
from utils.soft_get import soft_get
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


class TestObj(object):
    def __init__(self, obj, expected_fields, polarion_id):
        self.obj = obj
        self.expected_fields = expected_fields
        pytest.mark.polarion(polarion_id)(self)


TEST_OBJECTS = [
    TestObj(Container, [
            'name',
            'state',
            'last_state',
            'restart_count',
            'backing_ref_container_id',
            'privileged',
            'selinux_level'
            ], 'CMP-9945'),
    TestObj(Project, [
            'name',
            'creation_timestamp',
            'resource_version',
            ], 'CMP-10430'),
    TestObj(Route, [
            'name',
            'creation_timestamp',
            'resource_version',
            'host_name'
            ], 'CMP-9877'),
    TestObj(Pod, [
            'name',
            'phase',
            'creation_timestamp',
            'resource_version',
            'restart_policy',
            'dns_policy',
            'ip_address'
            ], 'CMP-9911'),
    TestObj(Node, [
            'name',
            'creation_timestamp',
            'resource_version',
            'number_of_cpu_cores',
            'memory',
            'max_pods_capacity',
            'system_bios_uuid',
            'machine_id',
            'infrastructure_machine_id',
            'runtime_version',
            'kubelet_version',
            'proxy_version',
            'operating_system_distribution',
            'kernel_version',
            ], 'CMP-9960'),
    TestObj(Image, {
            version.LOWEST:
                [
                    'name',
                    'tag',
                    'image_id',
                    'full_name'
                ],
            '5.7':
                [
                    'name',
                    'tag',
                    'image_id',
                    'full_name',
                    'architecture',
                    'author',
                    'entrypoint',
                    'docker_version',
                    'exposed_ports',
                    'size'
                ]
            }, 'CMP-9978'),
    TestObj(Service, [
            'name',
            'creation_timestamp',
            'resource_version',
            'session_affinity',
            'type',
            'portal_ip'
            ], 'CMP-9890'),
    TestObj(ImageRegistry, [
            'host'
            ], 'CMP-9988'),
    TestObj(Template, [
            'name',
            'creation_timestamp',
            'resource_version',
            ], 'CMP-10316')
]


@pytest.mark.parametrize('test_obj', TEST_OBJECTS,
                         ids=[obj.obj.__name__ for obj in TEST_OBJECTS])
def test_properties(provider, test_obj, soft_assert):

    if current_version() < "5.7" and test_obj.obj == Template:
        pytest.skip('Templates are not exist in CFME version lower than 5.7. skipping...')

    rows = navigate_and_get_rows(provider, test_obj.obj, 2)

    if not rows:
        pytest.skip('No records found for {}s. Skipping...'.format(test_obj.obj.__name__))
    names = [r[2].text for r in rows]

    if test_obj.obj is Container:
        args = [(r.pod_name.text, ) for r in rows]
    elif test_obj.obj is Image:
        args = [(r.tag.text, provider) for r in rows]
    else:
        args = [(provider, ) for _ in rows]

    for name, arg in zip(names, args):

        instance = test_obj.obj(name, *arg)
        navigate_to(instance, 'Details')
        if isinstance(test_obj.expected_fields, dict):
            expected_fields = version.pick(test_obj.expected_fields)
        else:
            expected_fields = test_obj.expected_fields
        for field in expected_fields:
            try:
                soft_get(instance.summary.properties, field)
            except AttributeError:
                soft_assert(False, '{} "{}" properties table has missing field - "{}"'
                                   .format(test_obj.obj.__name__, name, field))
