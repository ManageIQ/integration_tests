from random import choice

import pytest

from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator
from cfme.containers.container import Container
from cfme.containers.service import Service
from cfme.containers.pod import Pod
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(3),
    pytest.mark.provider([ContainersProvider], scope='function')
]


TEST_OBJECTS = [Replicator, Project, Route, Service, ContainersProvider, Pod, Container]


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
        view = navigate_to(obj, 'All')
        exist_member_str = choice(view.entities.entity_names)
        # Mapping the search string and the expected found result:
        search_strings_and_result = {
            '***': None,
            exist_member_str: exist_member_str,
            '$$$': None,
            exist_member_str[:len(exist_member_str) / 2]: exist_member_str
        }

        try:
            for search_string, result in search_strings_and_result.items():
                view.entities.search.search(search_string)
                results_row_names = view.entities.entity_names
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
            view.entities.search.clear_search()
