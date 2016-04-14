# -*- coding: utf-8 -*-

"""Run against fresh instance to ensure that the data checked is correct.
"""
import pytest
from fixtures.pytest_store import store
from utils import db_queries


@pytest.fixture
def appliance():
    return store.current_appliance


def test_configuration_details(appliance):
    result = db_queries.get_configuration_details(db=appliance.db)
    assert result is not None, "get_configuration_details returned None"


def test_server_name(appliance):
    assert store.current_appliance.server_name() == "EVM"


@pytest.mark.uncollectif(lambda: store.current_appliance.server_region() == 0)
def test_server_region_and_id(appliance):
    """Server ID begins with region number, so check that.
    """
    region = store.current_appliance.server_region()
    assert str(store.current_appliance.server_id()).startswith(str(region))
