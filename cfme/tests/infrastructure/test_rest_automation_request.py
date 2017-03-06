import pytest
from cfme import test_requirements
from cfme.rest.gen_data import automation_requests_data as _automation_requests_data
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from utils.wait import wait_for


pytestmark = [test_requirements.rest]


@pytest.fixture(scope="module")
def a_provider(request):
    return _a_provider(request)


@pytest.fixture(scope="module")
def vm(request, a_provider, rest_api_modscope):
    return _vm(request, a_provider, rest_api_modscope)


@pytest.fixture(scope="function")
def automation_requests_data(vm):
    return _automation_requests_data(vm)


@pytest.fixture(scope="function")
def automation_requests_pending(rest_api, vm):
    requests_data = _automation_requests_data(vm, approve=False)
    response = rest_api.collections.automation_requests.action.create(*requests_data)
    assert rest_api.response.status_code == 200
    for resource in response:
        assert resource.request_state == "pending"
    return response


def wait_for_requests(requests):
    def _finished():
        for request in requests:
            request.reload()
            if request.request_state != "finished":
                return False
        return True

    wait_for(_finished, num_sec=600, delay=5, message="automation_requests finished")


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "multiple", [False, True],
    ids=["one_request", "multiple_requests"])
def test_automation_requests(rest_api, automation_requests_data, multiple):
    """Test adding the automation request
     Prerequisities:
        * An appliance with ``/api`` available.
    Steps:
        * POST /api/automation_request - (method ``create``) add request
        * Retrieve list of entities using GET /api/automation_request and find just added request
    Metadata:
        test_flag: rest, requests
    """

    if multiple:
        requests = rest_api.collections.automation_requests.action.create(*automation_requests_data)
    else:
        requests = rest_api.collections.automation_requests.action.create(
            automation_requests_data[0])
    assert rest_api.response.status_code == 200

    wait_for_requests(requests)

    for request in requests:
        assert request.approval_state == "approved"
        resource = rest_api.collections.automation_requests.get(id=request.id)
        assert resource.type == "AutomationRequest"


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_approve_automation_requests(rest_api, automation_requests_pending, from_detail):
    """Tests approving automation requests.

    Metadata:
        test_flag: rest
    """
    if from_detail:
        for request in automation_requests_pending:
            request.action.approve(reason="I said so")
    else:
        rest_api.collections.automation_requests.action.approve(
            reason="I said so", *automation_requests_pending)
    assert rest_api.response.status_code == 200

    wait_for_requests(automation_requests_pending)

    for request in automation_requests_pending:
        request.reload()
        assert request.approval_state == "approved"


@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_deny_automation_requests(rest_api, automation_requests_pending, from_detail):
    """Tests denying automation requests.

    Metadata:
        test_flag: rest
    """
    if from_detail:
        for request in automation_requests_pending:
            request.action.deny(reason="I said so")
    else:
        rest_api.collections.automation_requests.action.deny(
            reason="I said so", *automation_requests_pending)
    assert rest_api.response.status_code == 200

    wait_for_requests(automation_requests_pending)

    for request in automation_requests_pending:
        request.reload()
        assert request.approval_state == "denied"
