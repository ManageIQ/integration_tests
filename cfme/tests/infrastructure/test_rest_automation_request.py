from __future__ import unicode_literals
import pytest
from cfme.rest import automation_requests_data as _automation_requests_data
from cfme.rest import a_provider as _a_provider
from cfme.rest import vm as _vm
from utils.wait import wait_for


@pytest.fixture(scope="module")
def a_provider():
    return _a_provider()


@pytest.fixture(scope="module")
def vm(request, a_provider, rest_api_modscope):
    return _vm(request, a_provider, rest_api_modscope)


@pytest.fixture(scope="module")
def automation_requests_data(vm):
    return _automation_requests_data(vm)


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "multiple", [False, True],
    ids=["one_request", "multiple_requests"])
def test_automation_requests(request, rest_api, automation_requests_data, multiple):
    """Test adding the automation request
     Prerequisities:
        * An appliance with ``/api`` available.
    Steps:
        * POST /api/automation_request - (method ``create``) add request
        * Retrieve list of entities using GET /api/automation_request and find just added request
    Metadata:
        test_flag: rest, requests
    """

    if "automation_requests" not in rest_api.collections:
        pytest.skip("automation request collection is not implemented in this version")

    if multiple:
        requests = rest_api.collections.automation_requests.action.create(*automation_requests_data)
    else:
        requests = rest_api.collections.automation_requests.action.create(
            automation_requests_data[0])

    def _finished():
        for request in requests:
            request.reload()
            if request.status.lower() not in {"error"}:
                return False
        return True

    wait_for(_finished, num_sec=600, delay=5, message="REST automation_request finishes")
