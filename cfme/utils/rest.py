"""Helper functions for tests using REST API."""
from collections import namedtuple

import pytest

from cfme.exceptions import OptionNotAvailable
from cfme.utils.wait import wait_for


def assert_response(
        rest_obj, success=None, http_status=None, results_num=None, task_wait=600):
    """
    Asserts that the response HTTP status code and content is as expected.

    If specific http_status is not given, we simply check that the status was a
    successful response code via requests.Response.__bool__()

    If response status code is '204', ensures there is no content.

    Example of verifying a success response:

    .. code-block:: python

        assert_response(appliance)

    Example of verifying a failure response:

    .. code-block:: python

        with error.expected('ActiveRecord::RecordNotFound'):
          collection.action.delete(some_stuff)
        assert_response(appliance, http_status=404)

    Note: For below args, 'results' refers to rest_obj.last_response.json()['results']

    Args:
        rest_obj -- instance of cfme.utils.Appliance (with rest_api attr defined)
            or cfme.utils.appliance.MiqApi
        success -- if defined, checks each result in results to ensure that result['success']
            is equal to the value defined here
        http_status (int or tuple of int) -- expected http response status codes, if None,
            we simply verify that the response was a success
        results_num (int) -- specifies expected number of results
        task_wait (int) -- if any result in results contains a 'task_id', this method will polls
            the API to ensure that task has moved to 'finished' and wait 'task_wait' seconds for
            that state change to occur
    """

    # check if `rest_obj` is an object with attribute referencing rest_api instance
    rest_api = rest_obj.rest_api if hasattr(rest_obj, 'rest_api') else rest_obj

    last_response = rest_api.response

    if http_status:
        # Convert single int to tuple if needed
        if isinstance(http_status, int):
            http_status = (http_status,)

        # Check the response codes
        assert last_response.status_code in http_status,\
            'The status code {} doesn\'t match the expected status code {}'.format(
                last_response.status_code, http_status)
    else:
        # No specific status_code specified, simply check if response was a success
        assert last_response, 'The request failed with {}'.format(last_response.status_code)

    try:
        content = last_response.json()
    except Exception:
        if last_response.status_code == 204:
            # 204 == No Content: check that message-body is empty and return
            assert not last_response.text.strip(), 'No content expected'
            return
        else:
            raise AssertionError('No JSON content returned')

    def _check_result(result):
        # check that result contains data to catch bugs like BZ 1414845
        assert result, 'The result should not be empty'

        if success is not None:
            assert 'success' in result
            assert result['success'] is success
        elif 'success' in result and last_response:
            # expect True if 'success' is present and HTTP status is success
            assert result['success'], 'The response "success" is {}'.format(result['success'])

        # if the request succeeded and there is a 'task_id' present in the response,
        # check the corresponding resource in /api/task/:task_id
        if task_wait and 'task_id' in result and result.get('success') and last_response:
            task = rest_api.get_entity('tasks', result['task_id'])
            task.wait_exists(num_sec=5)
            wait_for(
                lambda: task.state.lower() == 'finished',
                fail_func=task.reload,
                num_sec=task_wait,
                message='task state finished',
            )
            task_message = getattr(task, 'message', '')
            assert task.status.lower() == 'ok', (
                'Task failed with status "{}", message "{}"'.format(task.status, task_message))

    if 'results' in content:
        results = content['results']
        results_len = len(results)
        if results_num is not None:
            assert results_len == results_num,\
                'The number of results {} doesn\'t match the expected number {}'.format(
                    results_len, results_num)
        for result in results:
            _check_result(result)
    else:
        _check_result(content)

    # preserve the original response
    rest_api.response = last_response


def get_vms_in_service(service):
    """Gets list of vm entities associated with the service."""
    rest_api = service.collection._api
    service.vms.reload()
    # return entities under /api/vms, not under /api/services/:id/vms subcollection
    # where "actions" are not available
    return [rest_api.get_entity('vms', vm['id']) for vm in service.vms.all]


def create_resource(rest_api, col_name, col_data, col_action='create', substr_search=False):
    """Creates new resource in collection."""
    collection = getattr(rest_api.collections, col_name)
    try:
        action = getattr(collection.action, col_action)
    except AttributeError:
        raise OptionNotAvailable(
            "Action `{}` for {} is not implemented in this version".format(col_action, col_name))

    entities = action(*col_data)
    action_response = rest_api.response
    search_str = '%{}%' if substr_search else '{}'
    for entity in col_data:
        if entity.get('name'):
            wait_for(lambda: collection.find_by(
                name=search_str.format(entity.get('name'))) or False, num_sec=180, delay=10)
        elif entity.get('description'):
            wait_for(lambda: collection.find_by(
                description=search_str.format(entity.get('description'))) or False,
                num_sec=180, delay=10)
        else:
            raise NotImplementedError

    # make sure action response is preserved
    rest_api.response = action_response
    return entities


def delete_resources_from_collection(
        resources, collection=None, not_found=None, num_sec=10, delay=2, check_response=True):
    """Checks that delete from collection works as expected."""
    collection = collection or resources[0].collection

    def _assert_response(*args, **kwargs):
        if check_response:
            assert_response(collection._api, *args, **kwargs)

    collection.action.delete(*resources)
    _assert_response()

    for resource in resources:
        resource.wait_not_exists(num_sec=num_sec, delay=delay)

    if not_found:
        with pytest.raises(Exception, match='ActiveRecord::RecordNotFound'):
            collection.action.delete(*resources)
        _assert_response(http_status=404)
    else:
        collection.action.delete(*resources)
        _assert_response(success=False)


def delete_resources_from_detail(
        resources, method='POST', num_sec=10, delay=2, check_response=True):
    """Checks that delete from detail works as expected."""
    method = method.upper()
    rest_api = resources[0].collection._api

    def _assert_response(*args, **kwargs):
        if check_response:
            assert_response(rest_api, *args, **kwargs)

    for resource in resources:
        getattr(resource.action.delete, method)()
        _assert_response()

    # Wait for resource non-existence in separate loop so the delete actions are
    # not delayed by waiting for the previously deleted resource to disappear.
    # This way the combined wait time is likely to be much shorter.
    for resource in resources:
        resource.wait_not_exists(num_sec=num_sec, delay=delay)

        with pytest.raises(Exception, match='ActiveRecord::RecordNotFound'):
            getattr(resource.action.delete, method)()
        _assert_response(http_status=404)


def query_resource_attributes(resource, soft_assert=None):
    """Checks that all available attributes/subcollections are really accessible."""
    collection = resource.collection
    rest_api = collection._api
    options = rest_api.options(collection._href)
    attrs_to_query = options['virtual_attributes'] + options['relationships']
    subcolls_to_check = options['subcollections']

    FailedRecord = namedtuple('FailedRecord', ['name', 'type', 'error', 'response'])
    service_href = resource.href
    failed = []
    missing = []

    for attr in attrs_to_query:
        try:
            response = rest_api.get('{}?attributes={}'.format(service_href, attr))
            assert rest_api.response, 'Failed response'
        except Exception as err:
            failed.append(FailedRecord(attr, 'attribute', err, rest_api.response))
            continue

        if attr not in response:
            missing.append(attr)

    for subcol in subcolls_to_check:
        try:
            if subcol == 'metric_rollups':
                response = rest_api.get(
                    "{}/{}?capture_interval=hourly&start_date=2019-01-01".format(
                        service_href, subcol))
                assert rest_api.response, "Failed response"
                continue

            subcol_rest = getattr(resource, subcol)
            subcol_rest.reload()
        except Exception as err:
            failed.append(FailedRecord(subcol, 'subcollection', err, rest_api.response))

    outcome = namedtuple('AttrCheck', ['failed', 'missing'])(failed, missing)

    if soft_assert:
        for failure in outcome.failed:
            soft_assert(False, '{0} "{1}": status: {2}, error: `{3}`'.format(
                failure.type, failure.name, failure.response.status_code, failure.error))

    return outcome
