# -*- coding: utf-8 -*-
import pytest

from cfme.utils import testgen
from cfme.physical.provider.lenovo import LenovoProvider

pytestmark = [pytest.mark.tier(3)]

pytest_generate_tests = testgen.generate([LenovoProvider], scope="class")

@pytest.fixture(scope='class')
def api(appliance):
    return appliance.rest_api


@pytest.yield_fixture(scope="class")
def physical_server(provider, appliance):
    try:
        provider.create_rest()
        provider.refresh_provider_relationships
        physical_server = appliance.rest_api.collections.physical_servers[0]
        yield physical_server
    finally:
        if provider.exists:
            provider.delete_rest()
            provider.wait_for_delete_rest()


@pytest.fixture(scope='class')
def physical_servers_endpoint(physical_server):
    return physical_server.href


def test_get_hardware(api, physical_servers_endpoint):
    path = physical_servers_endpoint + '?attributes=hardware'
    api.get(path)
    assert api.response.ok
    assert api.response.json()['hardware'] is not None


def test_get_hardware_firmware(api, physical_servers_endpoint):
    path = physical_servers_endpoint + '?attributes=hardware.firmwares'
    api.get(path)
    assert api.response.ok
    assert api.response.json()['hardware']['firmwares'] is not None


def test_get_hardware_nics(api, physical_servers_endpoint):
    path = physical_servers_endpoint + '?attributes=hardware.nics'
    api.get(path)
    assert api.response.ok
    assert api.response.json()['hardware']['nics'] is not None


def test_get_hardware_ports(api, physical_servers_endpoint):
    path = physical_servers_endpoint + '?attributes=hardware.ports'
    api.get(path)
    assert api.response.ok
    assert api.response.json()['hardware']['ports'] is not None


def test_get_asset_details(api, physical_servers_endpoint):
    path = physical_servers_endpoint + '?attributes=asset_details'
    api.get(path)
    assert api.response.ok
    assert api.response.json()['asset_details'] is not None
