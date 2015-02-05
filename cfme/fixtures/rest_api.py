# -*- coding: utf-8 -*-
import pytest

from fixtures.pytest_store import store


@pytest.fixture(scope="function")
def rest_api():
    return store._current_appliance[-1].rest_api
