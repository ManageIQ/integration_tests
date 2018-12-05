# -*- coding: utf-8 -*-
"""REST API specific automate tests."""
from cfme import test_requirements


pytestmark = [test_requirements.rest]


def test_rest_search_automate(appliance):
    """
    Polarion:
        assignee: mkourim
        caseimportance: low
        initialEstimate: 1/3h
    """
    rest_api = appliance.rest_api

    def _do_query(**kwargs):
        response = rest_api.collections.automate.query_string(**kwargs)
        assert rest_api.response.status_code == 200
        return response

    more_depth = _do_query(depth='2')
    full_depth = _do_query(depth='-1')
    filtered_depth = _do_query(depth='-1', search_options='state_machines')
    assert len(full_depth) > len(more_depth) > len(rest_api.collections.automate)
    assert len(full_depth) > len(filtered_depth) > 0
