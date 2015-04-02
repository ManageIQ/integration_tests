# -*- coding: utf-8 -*-
"""This module handles connections to providers that are hidden in some private networks, accessible
by a VPN connection"""
import pytest

from fixtures.pytest_store import store
from utils import local_vpn


@pytest.yield_fixture(scope="module")
def provider_vpn(provider_data, provider_key):
    if "vpn" not in provider_data:
        yield
    else:
        with store.current_appliance.vpn_for(provider_key):
            with local_vpn.vpn_for(provider_key):
                yield
