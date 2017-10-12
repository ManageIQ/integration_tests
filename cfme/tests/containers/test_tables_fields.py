import pytest

from cfme.web_ui import PagedTable, toolbar as tb
from cfme.containers.pod import Pod
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.service import Service
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.container import Container
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.route import Route

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils import testgen


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9859')(
        ContainersTestItem(
            ContainersProvider, 'CMP-9859', fields_to_verify=['hostname', 'port', 'type']
        )
    ),
    pytest.mark.polarion('CMP-10651')(
        ContainersTestItem(
            Route, 'CMP-10651', fields_to_verify=['provider', 'project_name']
        )
    ),
    pytest.mark.polarion('CMP-9943')(
        ContainersTestItem(
            Container, 'CMP-9943', fields_to_verify=['pod_name', 'image', 'state']
        )
    ),
    pytest.mark.polarion('CMP-9909')(
        ContainersTestItem(
            Pod, 'CMP-9909', fields_to_verify=[
                'provider', 'project_name', 'ready', 'containers',
                'phase', 'restart_policy', 'dns_policy'
            ]
        )
    ),
    pytest.mark.polarion('CMP-9889')(
        ContainersTestItem(
            Service, 'CMP-9889', fields_to_verify=[
                'provider', 'project_name', 'type', 'portal_ip',
                'session_affinity', 'pods'
            ]
        )
    ),
    # TODO Add Node back into the list when other classes are updated to use WT views and widgets.
    # pytest.mark.polarion('CMP-9967')(
    #     ContainersTestItem(
    #         Node, 'CMP-9967', fields_to_verify=[
    #             'provider', 'ready', 'operating_system', 'kernel_version',
    #             'runtime_version'
    #         ]
    #     )
    # ),
    pytest.mark.polarion('CMP-9920')(
        ContainersTestItem(
            Replicator, 'CMP-9920',
            fields_to_verify=['provider', 'project_name', 'replicas', 'current_replicas']
        )
    ),
    pytest.mark.polarion('CMP-9975')(
        ContainersTestItem(
            Image, 'CMP-9975', fields_to_verify=['provider', 'tag', 'id', 'image_registry']
        )
    ),
    pytest.mark.polarion('CMP-9985')(
        ContainersTestItem(
            ImageRegistry, 'CMP-9985', fields_to_verify=['port', 'provider']
        )
    ),
    pytest.mark.polarion('CMP-10652')(
        ContainersTestItem(
            Project, 'CMP-9886', fields_to_verify=[
                'provider', 'container_routes', 'container_services',
                'container_replicators', 'pods', 'containers', 'images'
            ]
        )
    )
]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ti.args[1].pretty_id() for ti in TEST_ITEMS])
def test_tables_fields(provider, test_item, soft_assert):

    navigate_to(test_item.obj, 'All')
    tb.select('List View')
    # NOTE: We must re-instantiate here table
    # in order to prevent StaleElementException or UsingSharedTables
    # TODO: Switch to widgetastic
    paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")
    for row in paged_tbl.rows():
        cell = row[2]  # We're using indexing since it could be either 'name' or 'host'
        if cell:
            name = cell.text
        else:
            logger.error('Could not find NAME header on {}s list...'
                         .format(test_item.obj.__name__))
            continue
        for field in test_item.fields_to_verify:

            try:
                value = getattr(row, field)
            except AttributeError:
                soft_assert(False, '{}\'s list table: field  not exist: {}'
                            .format(test_item.obj.__name__, field))
                continue

            soft_assert(value, '{}\'s list table: {} row - has empty field: {}'
                        .format(test_item.obj.__name__, name, field))
