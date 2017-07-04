# -*- coding: utf-8 -*-
"""Helper functions for tests using REST API."""


def assert_response(appliance, success=None, http_status=None):
    """Asserts that the response HTTP status code and content is as expected."""

    last_response = appliance.rest_api.response

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
        for result in results:
            _check_result(result)
    else:
        _check_result(content)
