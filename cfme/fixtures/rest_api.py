# -*- coding: utf-8 -*-
"""Fixtures, providing an access to the CFME REST API.

See :py:func:`rest_api` and py:func:`rest_api_modscope`
"""
import pytest


@pytest.fixture(scope="function")
def rest_api():
    return pytest.store.current_appliance.rest_api


@pytest.fixture(scope="module")
def rest_api_modscope():
    return pytest.store.current_appliance.rest_api
