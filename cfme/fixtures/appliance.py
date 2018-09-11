""" This module contains fixtures to use when you need a temporary appliance for testing.

In cases where you cannot run a certain test againts the primary appliance because of the test's
destructive potential (which could render all subsequent testing useless), you want to use
a temporary appliance parallel to the primary one.

For tests where all you need is a single preconfigured appliance to run a database restore on for
example, you will want to use the :py:func:`temp_appliance_preconfig` fixture.

For tests that require multiple unconfigured appliances (e.g. replication testing), there is
:py:func:`temp_appliances_unconfig`.
"""
from contextlib import contextmanager

import pytest

from cfme.utils.version import get_stream
from cfme.test_framework.sprout.client import SproutClient


@contextmanager
def sprout_appliances(
    appliance,
    config,
    count=1,
    preconfigured=True,
    lease_time=120,
    stream=None,
    provider_type=None,
    version=None,
    **kwargs
):
    """ Provisions one or more appliances for testing

    Args:
        appliance: appliance object, used for version/stream defaults
        config: pytestconfig object to lookup sprout_user_key
        count: Number of appliances
        preconfigured: True if the appliance should be already configured, False otherwise
        lease_time: Lease time in minutes (3 hours by default)
        stream: defaults to appliance stream
        provider_type: no default, sprout chooses, string type otherwise
        version: defaults to appliance version, string type otherwise
    """
    sprout_client = SproutClient.from_config(sprout_user_key=config.option.sprout_user_key or None)
    # if version is passed and stream is not, don't default to appliance stream
    # if stream is passed and version is not, don't default to appliance version
    # basically, let stream/version work independently, and only default if neither are set
    req_version = version or (appliance.version.vstring if not stream else None)
    req_stream = stream or (appliance.version.stream() if not version else None)
    apps, request_id = sprout_client.provision_appliances(
        provider_type=provider_type,
        count=count,
        version=req_version,
        preconfigured=preconfigured,
        stream=req_stream,
        lease_time=lease_time,
        **kwargs
    )
    try:
        yield apps
    finally:
        sprout_client.destroy_pool(request_id)


# Single appliance, configured
@pytest.fixture(scope="module")
def temp_appliance_preconfig(temp_appliance_preconfig_modscope):
    yield temp_appliance_preconfig_modscope


@pytest.fixture(scope="module")
def temp_appliance_preconfig_modscope(appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=True) as appliances:
        yield appliances[0]


@pytest.fixture(scope="class")
def temp_appliance_preconfig_clsscope(appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=True) as appliances:
        yield appliances[0]


@pytest.fixture(scope="function")
def temp_appliance_preconfig_funcscope(appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=True) as appliances:
        yield appliances[0]


@pytest.fixture(scope="function")
def temp_appliance_preconfig_funcscope_upgrade(appliance, pytestconfig):
    stream_digits = ''.join([i for i in get_stream(appliance.version) if i.isdigit()])
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            preconfigured=True,
            stream="downstream-{}z".format(int(stream_digits) - 1)  # n-1 stream for upgrade
    ) as appliances:
        yield appliances[0]


# Single appliance, unconfigured
@pytest.fixture(scope="module")
def temp_appliance_unconfig(temp_appliance_unconfig_modscope):
    yield temp_appliance_unconfig_modscope


@pytest.fixture(scope="module")
def temp_appliance_unconfig_modscope(appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=False) as appliances:
        yield appliances[0]


@pytest.fixture(scope="class")
def temp_appliance_unconfig_clsscope(appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=False) as appliances:
        yield appliances[0]


@pytest.fixture(scope="function")
def temp_appliance_unconfig_funcscope(appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=False) as appliances:
        yield appliances[0]


@pytest.fixture(scope="function")
def temp_appliance_unconfig_funcscope_rhevm(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            preconfigured=False,
            provider_type='rhevm'
    ) as appliances:
        yield appliances[0]


# Pair of appliances, unconfigured
@pytest.fixture(scope="module")
def temp_appliances_unconfig(temp_appliances_unconfig_modscope):
    yield temp_appliances_unconfig_modscope


@pytest.fixture(scope="module")
def temp_appliances_unconfig_modscope(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False
    ) as appliances:
        yield appliances


@pytest.fixture(scope="function")
def temp_appliances_unconfig_funcscope_rhevm(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False,
            provider_type='rhevm'
    ) as appliances:
        yield appliances


@pytest.fixture(scope="class")
def temp_appliances_unconfig_clsscope(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False
    ) as appliances:
        yield appliances


@pytest.fixture(scope="function")
def temp_appliances_unconfig_funcscope(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False
    ) as appliances:
        yield appliances
