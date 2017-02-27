from random import choice

import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import search, toolbar as tb

from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.route import Route, list_tbl as route_list_tbl
from cfme.containers.project import Project, list_tbl as project_list_tbl
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator, list_tbl as replicator_list_tbl
from cfme.containers.container import Container, list_tbl as container_list_tbl
from cfme.containers.service import Service, list_tbl as service_list_tbl
from cfme.containers.pod import Pod, list_tbl as pod_list_tbl

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(3)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


class TestObj(object):
    def __init__(self, obj, list_tbl, polarion_id):
        self.obj = obj
        self.list_tbl = list_tbl
        pytest.mark.polarion(polarion_id)(self)


TEST_OBJECTS = [
    TestObj(Replicator, replicator_list_tbl, 'CMP-9923'),
    TestObj(Project, project_list_tbl, 'CMP-9871'),
    TestObj(Route, route_list_tbl, 'CMP-9921'),
    TestObj(Service, service_list_tbl, 'CMP-9922'),
    TestObj(ContainersProvider, container_list_tbl, 'CMP-9872'),
    TestObj(Pod, pod_list_tbl, 'CMP-10573'),
    TestObj(Container, container_list_tbl, 'CMP-10574')
]


@pytest.mark.parametrize('test_obj', TEST_OBJECTS, ids=[obj.obj for obj in TEST_OBJECTS])
def test_search_bar(test_obj):
    """ <object> summary page - Search bar
    This test checks Search bar functionality on every object summary page
    Steps:
        * Goes to <object> page
        * Inserts: Irregular symbol, '*' character, full search string, partial search string
        * Verify proper results
    """
    navigate_to(test_obj.obj, 'All')
    tb.select('List View')
    if sel.is_displayed_text("No Records Found."):
        pytest.skip('No Records Found in {} table. Could not test search. skipping...'
                    .format(test_obj.obj))
    rows = test_obj.list_tbl.rows_as_list()
    exist_member_str = choice(rows).name.text
    # Mapping the search string and the expected found result:
    search_strings_and_result = {
        '***': None,
        exist_member_str: exist_member_str,
        '$$$': None,
        exist_member_str[:len(exist_member_str) / 2]: exist_member_str
    }

    for search_string, result in search_strings_and_result.items():
        search.normal_search(search_string)
        results_row_names = ([r.name.text for r in test_obj.list_tbl.rows_as_list()]
                     if not sel.is_displayed_text("No Records Found.") else [])
        if result:
            if result not in results_row_names:
                raise Exception('Expected to get result "{}" '
                                'for search string "{}". search results: {}'
                                .format(result, search_string, results_row_names))
        else:
            if results_row_names:
                raise Exception('Unexpected result for search string "{}", '
                                'Should not find records, search results: "{}"'
                                .format(search_string, results_row_names))
