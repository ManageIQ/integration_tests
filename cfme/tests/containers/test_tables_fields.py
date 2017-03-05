import pytest

from utils import testgen
from cfme.web_ui import toolbar as tb

from cfme.containers.pod import Pod, paged_tbl as pod_paged_tbl
from cfme.containers.provider import ContainersProvider, paged_tbl as provider_paged_tbl
from cfme.containers.service import Service, paged_tbl as service_paged_tbl
from cfme.containers.node import Node, list_tbl as node_list_tbl
from cfme.containers.replicator import Replicator, paged_tbl as replicator_paged_tbl
from cfme.containers.image import Image, paged_tbl as image_paged_tbl
from cfme.containers.project import Project, paged_tbl as project_paged_tbl
from cfme.containers.container import Container, paged_tbl as container_paged_tbl
from cfme.containers.image_registry import ImageRegistry, paged_tbl as image_registry_paged_tbl
from cfme.containers.route import Route, list_tbl as route_list_tbl
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


class TestObj(object):
    def __init__(self, obj, paged_tbl, fields_to_verify, polarion_id):
        self.obj = obj
        self.paged_tbl = paged_tbl
        self.fields_to_verify = fields_to_verify
        pytest.mark.polarion(polarion_id)(self)


TEST_OBJECTS = [
    TestObj(ContainersProvider, provider_paged_tbl, [
        'hostname', 'port', 'type'
    ], 'CMP-9859'),
    TestObj(Route, route_list_tbl, [
        'provider', 'project_name'
    ], 'CMP-9875'),
    TestObj(Container, container_paged_tbl, [
        'pod_name', 'image', 'state'
    ], 'CMP-9943'),
    TestObj(Pod, pod_paged_tbl, [
        'provider', 'project_name', 'ready', 'containers',
        'phase', 'restart_policy', 'dns_policy'
    ], 'CMP-9909'),
    TestObj(Service, service_paged_tbl, [
        'provider', 'project_name', 'type', 'portal_ip', 'session_affinity', 'pods'
    ], 'CMP-9889'),
    TestObj(Node, node_list_tbl, [
        'provider', 'ready', 'operating_system', 'kernel_version', 'runtime_version'
    ], 'CMP-9967'),
    TestObj(Replicator, replicator_paged_tbl, [
        'provider', 'project_name', 'replicas', 'current_replicas'
    ], 'CMP-9920'),
    TestObj(Image, image_paged_tbl, [
        'provider', 'tag', 'id', 'image_registry'
    ], 'CMP-9975'),
    TestObj(ImageRegistry, image_registry_paged_tbl, [
        'port', 'provider'
    ], 'CMP-9985'),
    TestObj(Project, project_paged_tbl, [
        'provider', 'container_routes', 'container_services',
        'container_replicators', 'pods', 'containers', 'images'
    ], 'CMP-9886')
]


@pytest.mark.parametrize('test_obj', TEST_OBJECTS, ids=[obj.obj for obj in TEST_OBJECTS])
def test_tables_fields(provider, test_obj, soft_assert):

    navigate_to(test_obj.obj, 'All')
    tb.select('List View')
    for row in test_obj.paged_tbl.rows():
        name = row[2].text  # We're using indexing since it could be either 'Name' or 'Host'
        for field in test_obj.fields_to_verify:
            try:
                value = getattr(row, field)
            except AttributeError:
                soft_assert(False, '{}\'s list table: field  not exist: {}'
                            .format(test_obj.obj.__name__, field))
                continue
            soft_assert(value, '{}\'s list table: {} row - has empty field: {}'
                        .format(test_obj.obj.__name__, name, field))
