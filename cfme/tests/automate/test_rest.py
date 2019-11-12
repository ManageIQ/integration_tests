"""REST API specific automate tests."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail


pytestmark = [test_requirements.rest, pytest.mark.tier(3)]


@pytest.fixture(scope="function")
def domain_rest(appliance, domain):
    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alpha(), description=fauxfactory.gen_alpha(), enabled=True
    )
    yield appliance.rest_api.collections.automate_domains.get(name=domain.name)
    domain.delete_if_exists()


def test_rest_search_automate(appliance):
    """
    Polarion:
        assignee: pvala
        caseimportance: low
        casecomponent: Automate
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


@pytest.mark.ignore_stream("5.10")
@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_delete_automate_domain_from_detail(appliance, domain_rest, method):
    """
    Polarion:
        assignee: pvala
        casecomponent: Automate
        initialEstimate: 1/10h
    """
    delete_resources_from_detail([domain_rest], method=method, num_sec=50)


@pytest.mark.ignore_stream("5.10")
def test_delete_automate_domain_from_collection(appliance, domain_rest):
    """
    Polarion:
        assignee: pvala
        casecomponent: Automate
        initialEstimate: 1/10h
    """
    delete_resources_from_collection([domain_rest], not_found=True, num_sec=50)
