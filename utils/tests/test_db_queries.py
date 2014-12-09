# -*- coding: utf-8 -*-

"""Run against fresh instance to ensure that the data checked is correct.
"""
import pytest
from fixtures.pytest_store import store
from utils import db_queries


@pytest.fixture
def appliance_ip():
    return store.current_appliance.address


def test_configuration_details(appliance_ip):
    result = db_queries.get_configuration_details(ip_address=appliance_ip)
    assert result is not None, "get_configuration_details returned None"


def test_server_name(appliance_ip):
    assert store.current_appliance.server_name() == "EVM"


def test_server_region_and_id(appliance_ip):
    """Server ID begins with region number, so check that.
    """
    region = store.current_appliance.server_region()
    if region == 0:
        pytest.skip("Can't check this if the region is 0")
    assert str(store.current_appliance.server_id()).startswith(str(region))
