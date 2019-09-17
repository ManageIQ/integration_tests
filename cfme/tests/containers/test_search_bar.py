from random import choice

import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(3),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]


COLLECTION_NAMES = [
    'container_replicators',
    'container_projects',
    'container_routes',
    'container_services',
    'container_pods',
    'containers'
]


def test_search_bar(provider, appliance, soft_assert):
    """ <object> summary page - Search bar
    This test checks Search bar functionality on every object summary page
    Steps:
        * Goes to <object> page
        * Inserts: Irregular symbol, '*' character, full search string, partial search string
        * Verify proper results

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    for collection_name in COLLECTION_NAMES:
        view = navigate_to(getattr(appliance.collections, collection_name), 'All')
        exist_member_str = choice(view.entities.entity_names)
        # Mapping the search string and the expected found result:
        search_strings_and_result = {
            '***': None,
            exist_member_str: exist_member_str,
            '$$$': None,
            exist_member_str[:len(exist_member_str) // 2]: exist_member_str
        }

        try:
            for search_string, result in search_strings_and_result.items():
                view.entities.search.simple_search(search_string)
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
            view.entities.search.clear_simple_search()
