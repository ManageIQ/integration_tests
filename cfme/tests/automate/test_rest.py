"""REST API specific automate tests."""
from datetime import datetime

import fauxfactory
import pytest
from dateparser import parse

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.rest import assert_response
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
def test_delete_automate_domain_from_detail(domain_rest, method):
    """
    Polarion:
        assignee: pvala
        casecomponent: Automate
        initialEstimate: 1/10h
    """
    delete_resources_from_detail([domain_rest], method=method, num_sec=50)


@pytest.mark.ignore_stream("5.10")
def test_delete_automate_domain_from_collection(domain_rest):
    """
    Polarion:
        assignee: pvala
        casecomponent: Automate
        initialEstimate: 1/10h
    """
    delete_resources_from_collection([domain_rest], not_found=True, num_sec=50)


@pytest.mark.ignore_stream("5.10")
@pytest.mark.tier(2)
@pytest.mark.meta(
    automates=[1486765, 1740340],
    blockers=[BZ(1740340, unblock=lambda scheduler: scheduler != "exact_time")],
)
@pytest.mark.parametrize("scheduler", ["number_of_days", "exact_time"])
@test_requirements.rest
def test_schedule_automation_request(appliance, scheduler):
    """
    Bugzilla:
        1740340
        1486765

    Polarion:
        assignee: pvala
        caseimportance: high
        casecomponent: Rest
        initialEstimate: 1/4h
        testSteps:
            1. Send a request POST /api/automation_requests
                {
                    "uri_parts" : {
                        "namespace" : "System",
                        "class"     : "Request",
                        "instance"  : "InspectME",
                        "message"   : "create"
                    },
                    "parameters" : {
                        "var1" : "value 1",
                        "var2" : "value 2",
                        "minimum_memory" : 2048,
                        "schedule_time": scheduler
                    },
                    "requester" : {
                        "auto_approve" : true
                    }
                }
            2. Compare the `created_on` and `options::schedule_time` from the response.
        expectedResults:
            1. Request must be successful.
            2.Difference between the two dates must be equal to scheduler
    """
    schedule_time = "2" if scheduler == "number_of_days" else "2019-08-14 17:41:06 UTC"
    automate_request_rest = appliance.rest_api.collections.automation_requests.action.create(
        {
            "uri_parts": {
                "namespace": "System",
                "class": "Request",
                "instance": "InspectME",
                "message": "create",
            },
            "parameters": {
                "var1": "value 1",
                "var2": "value 2",
                "minimum_memory": 2048,
                "schedule_time": schedule_time,
            },
            "requester": {"auto_approve": True},
        }
    )[0]
    assert_response(appliance)

    automate_request = appliance.collections.automation_requests.instantiate(
        description=automate_request_rest.description
    )

    # This step tests another error that occurred when navigating to the Details page
    view = navigate_to(automate_request, "Details")
    assert view.is_displayed

    def _convert(date):
        # convert dates to a certain format for easy comparison
        date_format = "%m/%d/%y %H:%M"
        return datetime.strptime(datetime.strftime(date, date_format), date_format)

    scheduled = _convert(parse(automate_request_rest.options["schedule_time"]))

    if scheduler == "number_of_days":
        created_on = _convert(automate_request_rest.created_on)
        difference = scheduled - created_on
        assert str(difference.days) == schedule_time
    else:
        assert _convert(parse(schedule_time)) == scheduled
