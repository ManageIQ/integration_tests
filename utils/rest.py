# -*- coding: utf-8 -*-
"""Helper functions for tests using REST API."""


def assert_response(rest_obj, success=None, http_status=None, results_num=None):
    """Asserts that the response HTTP status code and content is as expected."""

    # check if `rest_obj` is an object with attribute referencing rest_api instance
    rest_api = rest_obj.rest_api if hasattr(rest_obj, 'rest_api') else rest_obj

    last_response = rest_api.response

    if http_status:
        assert last_response.status_code == http_status
    else:
        assert last_response

    try:
        content = last_response.json()
    except Exception:
        if last_response.status_code == 204:
            # 204 == No Content: check that message-body is empty and return
            assert not last_response.text.strip()
            return
        else:
            raise AssertionError("No content returned")

    def _check_result(result):
        if success is not None:
            assert 'success' in result
            assert result['success'] is success
        elif 'success' in result and last_response:
            # expect True if 'success' is present and HTTP status is success
            assert result['success']

    if 'results' in content:
        results = content['results']
        if results_num is not None:
            assert len(results) == results_num
        for result in results:
            _check_result(result)
    else:
        _check_result(content)


def get_vms_in_service(rest_api, service):
    """Gets list of vm entities associated with the service."""
    service.vms.reload()
    # return entities under /api/vms, not under /api/services/:id/vms subcollection
    # where "actions" are not available
    return [rest_api.get_entity('vms', vm['id']) for vm in service.vms.all]
