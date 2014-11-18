# -*- coding: utf-8 -*-
"""Fixture providing SNMP client for tests that want it."""
import pytest
from urlparse import urlparse

from fixtures.pytest_store import store
from utils.snmp_client import SNMPClient


@pytest.fixture(scope="function")
def snmp_client(ssh_client):
    return SNMPClient(urlparse(store.base_url).netloc)
