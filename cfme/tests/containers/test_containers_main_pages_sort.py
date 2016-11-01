import pytest
from utils import testgen
from utils.version import current_version
from cfme.web_ui import toolbar, SortTable
from cfme.containers.project import Project
from cfme.containers.replicator import Replicator
from cfme.containers.service import Service
from cfme.containers.route import Route
from cfme.containers.provider import ContainersProvider
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9924 CMP-9925 CMP-9926 CMP-9927 CMP-9928


TEST_OBJECTS = [Project, Service, Replicator, Route, ContainersProvider]


@pytest.mark.parametrize('cls', TEST_OBJECTS)
def test_containers_main_pages_sort(cls):

    navigate_to(cls, 'All')
    toolbar.select('List View')
    # NOTE: We must re-instantiate here sort_tbl in order to prevent StaleElementException
    sort_tbl = SortTable(table_locator="//div[@id='list_grid']//table")
    header_texts = [header.text for header in sort_tbl.headers]
    for col, header_text in enumerate(header_texts):

        if not header_text:
            continue

        # Checking both orders
        sort_tbl.sort_by(header_text, 'ascending')
        rows_ascending = [r[col].text for r in sort_tbl.rows()]
        sort_tbl.sort_by(header_text, 'descending')
        rows_descending = [r[col].text for r in sort_tbl.rows()]

        assert rows_ascending[::-1] == rows_descending
