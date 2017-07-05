# -*- coding: utf-8 -*-
"""Fixtures, providing an access to the CFME REST API.

See :py:func:`rest_api` and py:func:`rest_api_modscope`
"""
from __future__ import absolute_import
import pytest


@pytest.fixture(scope="function")
def rest_api(appliance):
    return appliance.rest_api


@pytest.fixture(scope="module")
def rest_api_modscope(appliance):
    return appliance.rest_api
