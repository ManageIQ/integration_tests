# -*- coding: utf-8 -*-
"""Fixture providing SNMP client for tests that want it."""
import pytest
from urlparse import urlparse

from fixtures.pytest_store import store
from utils.snmp_client import SNMPClient


@pytest.yield_fixture(scope="function")
def snmp_client(ssh_client):
    """Provides SNMP Client that gets installed on the CFME machine.

    ssh_client fixture is specified because the SNMPClient installs it using SSH.
    """
    client = SNMPClient(urlparse(store.base_url).netloc)
    client.check_installed()
    client.flush()
    yield client
    client.flush()
