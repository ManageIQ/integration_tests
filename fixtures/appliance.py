""" This module contains fixtures to use when you need a temporary appliance for testing.

In cases where you cannot run a certain test againts the primary appliance because of the test's
destructive potential (which could render all subsequent testing useless), you want to use
a temporary appliance parallel to the primary one.

For tests such as setting up an appliance (or multiple) in a certain setup, you will want to use
the :py:func:`temp_appliance_unconfig` fixture and then configure the appliance(s) yourself.

For tests where all you need is a single preconfigured appliance to run a database restore on for
example, you will want to use the :py:func:`temp_appliance_preconfig` fixture.

For tests that require multiple unconfigured appliances (e.g. replication testing), there is
:py:func:`temp_appliances_unconfig`.
"""
from contextlib import contextmanager

import pytest

from cfme.test_framework.sprout.client import SproutClient


@contextmanager
def temp_appliances(count=1, preconfigured=True, lease_time=180):
    """ Provisions one or more appliances for testing

    Args:
        count: Number of appliances
        preconfigured: True if the appliance should be already configured, False otherwise
        lease_time: Lease time in minutes (3 hours by default)
    """
    try:
        sprout_client = SproutClient.from_config()
        apps, request_id = sprout_client.provision_appliances(
            count=count, lease_time=lease_time, preconfigured=preconfigured)
        yield apps
    finally:
        sprout_client.destroy_pool(request_id)


# Single appliance, configured
@pytest.yield_fixture(scope="module")
def temp_appliance_preconfig(temp_appliance_preconfig_modscope):
    yield temp_appliance_preconfig_modscope


@pytest.yield_fixture(scope="module")
def temp_appliance_preconfig_modscope():
    with temp_appliances(preconfigured=True) as appliances:
        yield appliances[0]


@pytest.yield_fixture(scope="class")
def temp_appliance_preconfig_clsscope():
    with temp_appliances(preconfigured=True) as appliances:
        yield appliances[0]


@pytest.yield_fixture(scope="function")
def temp_appliance_preconfig_funcscope():
    with temp_appliances(preconfigured=True) as appliances:
        yield appliances[0]


# Single appliance, unconfigured
@pytest.yield_fixture(scope="module")
def temp_appliance_unconfig(temp_appliance_unconfig_modscope):
    yield temp_appliance_unconfig_modscope


@pytest.yield_fixture(scope="module")
def temp_appliance_unconfig_modscope():
    with temp_appliances(preconfigured=False) as appliances:
        yield appliances[0]


@pytest.yield_fixture(scope="class")
def temp_appliance_unconfig_clsscope():
    with temp_appliances(preconfigured=False) as appliances:
        yield appliances[0]


@pytest.yield_fixture(scope="function")
def temp_appliance_unconfig_funcscope():
    with temp_appliances(preconfigured=False) as appliances:
        yield appliances[0]


# Pair of appliances, unconfigured
@pytest.yield_fixture(scope="module")
def temp_appliances_unconfig(temp_appliances_unconfig_modscope):
    yield temp_appliances_unconfig_modscope


@pytest.yield_fixture(scope="module")
def temp_appliances_unconfig_modscope():
    with temp_appliances(count=2, preconfigured=False) as appliances:
        yield appliances


@pytest.yield_fixture(scope="class")
def temp_appliances_unconfig_clsscope():
    with temp_appliances(count=2, preconfigured=False) as appliances:
        yield appliances


@pytest.yield_fixture(scope="function")
def temp_appliances_unconfig_funcscope():
    with temp_appliances(count=2, preconfigured=False) as appliances:
        yield appliances
