from random import choice

import pytest

from utils import testgen
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import search, CheckboxTable

from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider, navigate_and_get_rows
from cfme.containers.replicator import Replicator
from cfme.containers.container import Container
from cfme.containers.service import Service
from cfme.containers.pod import Pod

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(3)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


TEST_OBJECTS = [
    Replicator,
    Project,
    Route,
    Service,
    ContainersProvider,
    Pod,
    Container
]


@pytest.mark.polarion('CMP-10577')
def test_search_bar(provider, soft_assert):
    """ <object> summary page - Search bar
    This test checks Search bar functionality on every object summary page
    Steps:
        * Goes to <object> page
        * Inserts: Irregular symbol, '*' character, full search string, partial search string
        * Verify proper results
    """
    for obj in TEST_OBJECTS:
        rows = navigate_and_get_rows(provider, obj, 1)
        if not rows:
            pytest.skip('No Records Found in {} table. Could not test search. skipping...'
                        .format(obj))
        exist_member_str = choice(rows).name.text
        # Mapping the search string and the expected found result:
        search_strings_and_result = {
            '***': None,
            exist_member_str: exist_member_str,
            '$$$': None,
            exist_member_str[:len(exist_member_str) / 2]: exist_member_str
        }

        try:
            for search_string, result in search_strings_and_result.items():
                search.normal_search(search_string)
                # NOTE: We must re-instantiate here table
                # in order to prevent StaleElementException or UsingSharedTables
                list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
                results_row_names = ([r.name.text for r in list_tbl.rows_as_list()]
                             if not sel.is_displayed_text("No Records Found.") else [])
                if result:
                    soft_assert(result in results_row_names,
                        'Expected to get result "{}" '
                        'for search string "{}". search results: {}'
                        .format(result, search_string, results_row_names))
                else:
                    soft_assert(not results_row_names,
                        'Unexpected result for search string "{}", '
                        'Should not find records, search results: "{}"'
                        .format(search_string, results_row_names))
        finally:
            # search.ensure_no_filter_applied() -> TimedOutError
            # https://github.com/ManageIQ/integration_tests/issues/4401
            search.normal_search("")
