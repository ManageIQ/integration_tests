""" This module contains fixtures to use when you need a temporary appliance for testing.

In cases where you cannot run a certain test againts the primary appliance because of the test's
destructive potential (which could render all subsequent testing useless), you want to use
a temporary appliance parallel to the primary one.

For tests such as setting up an appliance (or multiple) in a certain setup, you will want to use
the :py:func:`temp_appliance_unconfig` fixture and then configure the appliance(s) yourself.

For tests where all you need is a single preconfigured appliance to run a database restore on, for
example, you will want to use the :py:func:`temp_appliance_preconfig` fixture.
"""
from contextlib import contextmanager

import pytest

from cfme.test_framework.sprout.client import SproutClient


@contextmanager
def _temp_appliance(preconfigured=True, lease_time=180):
    """ Provisions a temporary appliance for testing

    Args:
        preconfigured: True if the appliance should be already configured, False otherwise
        lease_time: Lease time in minutes (3 hours by default)
    """
    sprout_client = SproutClient.from_config()
    apps, request_id = sprout_client.provision_appliances(
        lease_time=lease_time, preconfigured=preconfigured)
    app = apps[0]
    app.stop_evm_service()
    app.extend_db_partition()
    app.start_evm_service()
    yield app
    sprout_client.destroy_pool(request_id)


@pytest.yield_fixture(scope="module")
def temp_appliance_preconfig(temp_appliance_preconfig_modscope):
    yield temp_appliance_preconfig_modscope


@pytest.yield_fixture(scope="module")
def temp_appliance_preconfig_modscope():
    with _temp_appliance(preconfigured=True) as appliance:
        yield appliance


@pytest.yield_fixture(scope="class")
def temp_appliance_preconfig_clsscope():
    with _temp_appliance(preconfigured=True) as appliance:
        yield appliance


@pytest.yield_fixture(scope="function")
def temp_appliance_preconfig_funcscope():
    with _temp_appliance(preconfigured=True) as appliance:
        yield appliance


@pytest.yield_fixture(scope="module")
def temp_appliance_unconfig(temp_appliance_unconfig_modscope):
    yield temp_appliance_unconfig_modscope


@pytest.yield_fixture(scope="module")
def temp_appliance_unconfig_modscope():
    with _temp_appliance(preconfigured=False) as appliance:
        yield appliance


@pytest.yield_fixture(scope="class")
def temp_appliance_unconfig_clsscope():
    with _temp_appliance(preconfigured=False) as appliance:
        yield appliance


@pytest.yield_fixture(scope="function")
def temp_appliance_unconfig_funcscope():
    with _temp_appliance(preconfigured=False) as appliance:
        yield appliance
