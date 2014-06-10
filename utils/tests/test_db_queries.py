# -*- coding: utf-8 -*-

"""Run against fresh instance to ensure that the data checked is correct.
"""
import pytest
from utils import db_queries
from utils.conf import env
from urlparse import urlparse


@pytest.fixture
def appliance_ip():
    return urlparse(env["base_url"]).netloc


def test_configuration_details(appliance_ip):
    result = db_queries.get_configuration_details(appliance_ip)
    assert result is not None, "get_configuration_details returned None"


def test_server_name(appliance_ip):
    assert db_queries.get_server_name(appliance_ip) == "EVM"


def test_server_region_and_id(appliance_ip):
    """Server ID begins with region number, so check that.
    """
    region = db_queries.get_server_region(appliance_ip)
    if region == 0:
        pytest.skip("Can't check this if the region is 0")
    assert str(db_queries.get_server_id(appliance_ip)).startswith(str(region))
