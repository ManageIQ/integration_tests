# -*- coding: utf-8 -*-
"""Helper functions for tests using REST API."""

from cfme.utils.wait import wait_for


def assert_response(
        rest_obj, success=None, http_status=None, results_num=None, task_wait=600):
    """Asserts that the response HTTP status code and content is as expected."""

    # check if `rest_obj` is an object with attribute referencing rest_api instance
    rest_api = rest_obj.rest_api if hasattr(rest_obj, 'rest_api') else rest_obj

    last_response = rest_api.response

    if http_status:
        assert last_response.status_code == http_status,\
            'The status code {} doesn\'t match the expected status code {}'.format(
                last_response.status_code, http_status)
    else:
        assert last_response, 'The request failed with {}'.format(last_response.status_code)

    try:
        content = last_response.json()
    except Exception:
        if last_response.status_code == 204:
            # 204 == No Content: check that message-body is empty and return
            assert not last_response.text.strip(), 'No content expected'
            return
        else:
            raise AssertionError('No content returned')

    def _check_result(result):
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
            wait_for(
                lambda: task.state.lower() == 'finished',
                fail_func=task.reload,
                num_sec=task_wait,
                message='task state finished',
            )
            assert task.status.lower() == 'ok', 'Task failed with status "{}"'.format(task.status)

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


def get_vms_in_service(rest_api, service):
    """Gets list of vm entities associated with the service."""
    service.vms.reload()
    # return entities under /api/vms, not under /api/services/:id/vms subcollection
    # where "actions" are not available
    return [rest_api.get_entity('vms', vm['id']) for vm in service.vms.all]
