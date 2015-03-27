# -*- coding: utf-8 -*-
"""Fixtures, providing an access to the CFME REST API.

See :py:func:`rest_api` and py:func:`rest_api_modscope
"""
import pytest

from fixtures.pytest_store import store


@pytest.fixture(scope="function")
def rest_api():
    return store._current_appliance[-1].rest_api


@pytest.fixture(scope="module")
def rest_api_modscope():
    return store._current_appliance[-1].rest_api
