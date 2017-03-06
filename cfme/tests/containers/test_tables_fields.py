import pytest

from utils import testgen
from cfme.web_ui import PagedTable, toolbar as tb

from cfme.containers.pod import Pod
from cfme.containers.provider import ContainersProvider
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.container import Container
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.route import Route
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


class TestObj(object):
    def __init__(self, obj, fields_to_verify, polarion_id):
        self.obj = obj
        self.fields_to_verify = fields_to_verify
        pytest.mark.polarion(polarion_id)(self)


TEST_OBJECTS = [
    TestObj(ContainersProvider, [
        'hostname', 'port', 'type'
    ], 'CMP-9859'),
    TestObj(Route, [
        'provider', 'project_name'
    ], 'CMP-9875'),
    TestObj(Container, [
        'pod_name', 'image', 'state'
    ], 'CMP-9943'),
    TestObj(Pod, [
        'provider', 'project_name', 'ready', 'containers',
        'phase', 'restart_policy', 'dns_policy'
    ], 'CMP-9909'),
    TestObj(Service, [
        'provider', 'project_name', 'type', 'portal_ip', 'session_affinity', 'pods'
    ], 'CMP-9889'),
    TestObj(Node, [
        'provider', 'ready', 'operating_system', 'kernel_version', 'runtime_version'
    ], 'CMP-9967'),
    TestObj(Replicator, [
        'provider', 'project_name', 'replicas', 'current_replicas'
    ], 'CMP-9920'),
    TestObj(Image, [
        'provider', 'tag', 'id', 'image_registry'
    ], 'CMP-9975'),
    TestObj(ImageRegistry, [
        'port', 'provider'
    ], 'CMP-9985'),
    TestObj(Project, [
        'provider', 'container_routes', 'container_services',
        'container_replicators', 'pods', 'containers', 'images'
    ], 'CMP-9886')
]


@pytest.mark.parametrize('test_obj', TEST_OBJECTS, ids=[obj.obj for obj in TEST_OBJECTS])
def test_tables_fields(provider, test_obj, soft_assert):

    navigate_to(test_obj.obj, 'All')
    tb.select('List View')
    # NOTE: We must re-instantiate here table
    # in order to prevent StaleElementException or UsingSharedTables
    paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")
    for row in paged_tbl.rows():
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
