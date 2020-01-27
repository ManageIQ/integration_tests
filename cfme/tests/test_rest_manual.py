"""Manual tests"""
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.appliance.implementations.ui import ViaUI

pytestmark = [pytest.mark.manual]


@test_requirements.rest
@pytest.mark.customer_scenario
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1700378])
def test_notification_url_parallel_requests():
    """
    Bugzilla:
        1700378
        1714615

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        testSteps:
            1. Stop evmserverd.
            2. Run `bin rails/server`
            3. Monitor production.log
            4. Run ruby script which will execute multiple api requests parallely.
                ```
                2.times do
                    Thread.new do
                        `curl -L https://admin:smartvm@localhost/api/vms`
                    end
                    Thread.new do
                        `curl -L https://admin:smartvm@localhost/api/notifications?
                        expand=resources&attributes=details&sort_by=id&sort_order=desc&limit=100`
                    end
                end
                ```
            5. Validate logs.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Check if all the requests were processed and completed
    """
    pass


@pytest.mark.meta(coverage=[1761836])
@pytest.mark.tier(3)
@test_requirements.rest
@pytest.mark.parametrize("context", [ViaUI, ViaREST])
def test_widget_generate_content_via_rest(context):
    """
    Bugzilla:
       1761836
       1623607
       1753682

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        testSteps:
            1. Depending on the implementation -
                i. GET /api/widgtes/:id and note the `last_generated_content_on`.
                ii. Navigate to Dashboard and note the `last_generated_content_on` for the widget.
            2. POST /api/widgets/:id
                {
                    "action": "generate_content"
                }
            3. Wait until the task completes.
            4. Depending on the implementation
                i. GET /api/widgets/:id and compare the value of `last_generated_content_on`
                    with the value noted in step 1.
                ii.  Navigate to the dashboard and check if the value was updated for the widget.
        expectedResults:
            1.
            2.
            3.
            4. Both values must be different, value must be updated.
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1486765, 1740340])
@pytest.mark.parametrize(
    "scheduler", ["2", "2019-08-14 17:41:06 UTC"], ids=["number_of_days", "exact_time"]
)
@test_requirements.rest
def test_schedule_automation_request(scheduler):
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
    pass
