import multiprocessing as mp

import pytest

from manageiq_client.api import ManageIQClient as MiqApi

from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import automation_requests_data as _automation_requests_data
from cfme.rest.gen_data import vm as _vm
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for
from fixtures.pytest_store import store


pytestmark = [test_requirements.rest]


@pytest.fixture(scope='module')
def a_provider(request):
    return _a_provider(request)


@pytest.fixture(scope='module')
def vm(request, a_provider, appliance):
    return _vm(request, a_provider, appliance.rest_api)


def wait_for_requests(requests):
    def _finished():
        for request in requests:
            request.reload()
            if request.request_state != 'finished':
                return False
        return True

    wait_for(_finished, num_sec=600, delay=5, message="automation_requests finished")


def gen_pending_requests(collection, rest_api, vm, requests=False):
    requests_data = _automation_requests_data(vm, approve=False, requests_collection=requests)
    response = collection.action.create(*requests_data[:2])
    assert_response(rest_api)
    assert len(response) == 2
    for resource in response:
        assert resource.request_state == 'pending'
    return response


def create_requests(collection, rest_api, automation_requests_data, multiple):
    if multiple:
        requests = collection.action.create(*automation_requests_data)
    else:
        requests = collection.action.create(
            automation_requests_data[0])
    assert_response(rest_api)

    wait_for_requests(requests)

    for request in requests:
        assert request.approval_state == 'approved'
        resource = collection.get(id=request.id)
        assert resource.type == 'AutomationRequest'


def create_pending_requests(collection, rest_api, requests_pending):
    # The `approval_state` is `pending_approval`. Wait to see that
    # it does NOT change - that would mean the request was auto-approved.
    # The `wait_for` is expected to fail.
    # It's enough to wait just for the first request, it gives
    # other requests the same amount of time to change state.
    waiting_request = requests_pending[0]
    wait_for(
        lambda: waiting_request.approval_state != 'pending_approval',
        fail_func=waiting_request.reload,
        num_sec=30,
        delay=10,
        silent_failure=True)

    for request in requests_pending:
        request.reload()
        assert request.approval_state == 'pending_approval'
        resource = collection.get(id=request.id)
        assert_response(rest_api)
        assert resource.type == 'AutomationRequest'


def approve_requests(collection, rest_api, requests_pending, from_detail):
    if from_detail:
        for request in requests_pending:
            request.action.approve(reason="I said so")
    else:
        collection.action.approve(
            reason="I said so", *requests_pending)
    assert_response(rest_api)

    wait_for_requests(requests_pending)

    for request in requests_pending:
        request.reload()
        assert request.approval_state == 'approved'


def deny_requests(collection, rest_api, requests_pending, from_detail):
    if from_detail:
        for request in requests_pending:
            request.action.deny(reason="I said so")
    else:
        collection.action.deny(
            reason="I said so", *requests_pending)
    assert_response(rest_api)

    wait_for_requests(requests_pending)

    for request in requests_pending:
        request.reload()
        assert request.approval_state == 'denied'


def edit_requests(collection, rest_api, requests_pending, from_detail):
    body = {'options': {'arbitrary_key_allowed': 'test_rest'}}

    if from_detail:
        # testing BZ 1418331
        for request in requests_pending:
            request.action.edit(**body)
            assert_response(rest_api)
    else:
        identifiers = []
        for i, resource in enumerate(requests_pending):
            loc = ({'id': resource.id}, {'href': '{}/{}'.format(collection._href, resource.id)})
            identifiers.append(loc[i % 2])
        collection.action.edit(*identifiers, **body)
        assert_response(rest_api)

    for request in requests_pending:
        request.reload()
        assert request.options['arbitrary_key_allowed'] == 'test_rest'


class TestAutomationRequestsRESTAPI(object):
    """Tests using /api/automation_requests."""

    @pytest.fixture(scope='function')
    def collection(self, appliance):
        return appliance.rest_api.collections.automation_requests

    @pytest.fixture(scope='function')
    def automation_requests_data(self, vm):
        return _automation_requests_data(vm)

    @pytest.fixture(scope='function')
    def requests_pending(self, appliance, vm):
        return gen_pending_requests(
            appliance.rest_api.collections.automation_requests, appliance.rest_api, vm)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'multiple', [False, True],
        ids=['one_request', 'multiple_requests'])
    def test_create_requests(self, collection, appliance, automation_requests_data, multiple):
        """Test adding the automation request using /api/automation_requests.

        Metadata:
            test_flag: rest, requests
        """
        create_requests(collection, appliance.rest_api, automation_requests_data, multiple)

    @pytest.mark.tier(3)
    def test_create_pending_requests(self, appliance, requests_pending, collection):
        """Tests creating pending requests using /api/automation_requests.

        Metadata:
            test_flag: rest, requests
        """
        create_pending_requests(collection, appliance.rest_api, requests_pending)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_approve_requests(self, collection, appliance, requests_pending, from_detail):
        """Tests approving automation requests using /api/automation_requests.

        Metadata:
            test_flag: rest, requests
        """
        approve_requests(collection, appliance.rest_api, requests_pending, from_detail)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_deny_requests(self, collection, appliance, requests_pending, from_detail):
        """Tests denying automation requests using /api/automation_requests.

        Metadata:
            test_flag: rest, requests
        """
        deny_requests(collection, appliance.rest_api, requests_pending, from_detail)

    @pytest.mark.tier(3)
    @pytest.mark.skipif(
        store.current_appliance.version < '5.9',
        reason='BZ 1418338 was fixed only for versions >= 5.9')
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_requests(self, collection, appliance, requests_pending, from_detail):
        """Tests editing requests using /api/automation_requests.

        Metadata:
            test_flag: rest, requests
        """
        # testing BZ 1418338
        edit_requests(collection, appliance.rest_api, requests_pending, from_detail)


class TestAutomationRequestsCommonRESTAPI(object):
    """Tests using /api/requests (common collection for all requests types)."""

    @pytest.fixture(scope='function')
    def collection(self, appliance):
        return appliance.rest_api.collections.requests

    @pytest.fixture(scope='function')
    def automation_requests_data(self, vm):
        return _automation_requests_data(vm, requests_collection=True)

    @pytest.fixture(scope='function')
    def requests_pending(self, appliance, vm):
        return gen_pending_requests(
            appliance.rest_api.collections.requests, appliance.rest_api, vm, requests=True)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'multiple', [False, True],
        ids=['one_request', 'multiple_requests'])
    def test_create_requests(self, collection, appliance, automation_requests_data, multiple):
        """Test adding the automation request using /api/requests.

        Metadata:
            test_flag: rest, requests
        """
        create_requests(collection, appliance.rest_api, automation_requests_data, multiple)

    @pytest.mark.tier(3)
    def test_create_pending_requests(self, collection, appliance, requests_pending):
        """Tests creating pending requests using /api/requests.

        Metadata:
            test_flag: rest, requests
        """
        create_pending_requests(collection, appliance.rest_api, requests_pending)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_approve_requests(self, collection, appliance, requests_pending, from_detail):
        """Tests approving automation requests using /api/requests.

        Metadata:
            test_flag: rest, requests
        """
        approve_requests(collection, appliance.rest_api, requests_pending, from_detail)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_deny_requests(self, collection, appliance, requests_pending, from_detail):
        """Tests denying automation requests using /api/requests.

        Metadata:
            test_flag: rest, requests
        """
        deny_requests(collection, appliance.rest_api, requests_pending, from_detail)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_requests(self, collection, appliance, requests_pending, from_detail):
        """Tests editing requests using /api/requests.

        Metadata:
            test_flag: rest, requests
        """
        edit_requests(collection, appliance.rest_api, requests_pending, from_detail)

    def test_create_requests_parallel(self, appliance):
        """Create automation requests in parallel.

        Metadata:
            test_flag: rest, requests
        """
        output = mp.Queue()
        entry_point = appliance.rest_api._entry_point
        auth = appliance.rest_api._auth

        def _gen_automation_requests(output):
            api = MiqApi(entry_point, auth, verify_ssl=False)
            requests_data = _automation_requests_data(
                'nonexistent_vm', requests_collection=True, approve=False)
            api.collections.requests.action.create(*requests_data[:2])
            result = (api.response.status_code, api.response.json())
            output.put(result)

        processes = [
            mp.Process(target=_gen_automation_requests, args=(output,))
            for _ in range(4)]

        for proc in processes:
            proc.start()

        # wait for all processes to finish
        for proc in processes:
            proc.join()

        for proc in processes:
            status, response = output.get()
            assert status == 200
            for result in response['results']:
                assert result['request_type'] == 'automation'
