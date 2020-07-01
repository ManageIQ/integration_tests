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

from cfme.test_framework.sprout.client import SproutClient
from cfme.utils import conf
from cfme.utils import periodic_call
from cfme.utils.log import logger


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
        lease_time: Lease time in minutes (2 hours by default)
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

    if config.getoption("update_appliance"):
        for app in apps:
            logger.info("Initiating appliance update on temp appliance ...")
            urls = config.getoption("update_urls")
            app.update_rhel(*urls, reboot=True)
            # Web UI not available on unconfigured appliances
            if preconfigured:
                logger.info("Appliance update finished on temp appliance, waiting for UI ...")
                app.wait_for_miq_ready()
            logger.info("Appliance update finished on temp appliance...")

    try:
        # Renew in half the lease time interval which is number of minutes.
        with periodic_call(lease_time * 60 / 2.,
                           sprout_client.prolong_pool, (request_id, lease_time)):
            yield apps
    finally:
        sprout_client.destroy_pool(request_id)


# Single appliance, configured
@pytest.fixture(scope="module")
def temp_appliance_preconfig(temp_appliance_preconfig_modscope):
    yield temp_appliance_preconfig_modscope


@pytest.fixture(scope="module")
def temp_appliance_preconfig_modscope(request, appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=True) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="class")
def temp_appliance_preconfig_clsscope(request, appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=True) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliance_preconfig_funcscope(request, appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=True) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliance_preconfig_funcscope_upgrade(request, appliance, pytestconfig):
    split_version = (str(appliance.version).split("."))
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            preconfigured=True,
            stream="downstream-{}{}z".format(
                split_version[0], (int(split_version[1]) - 1)
            )  # n-1 stream for upgrade
    ) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="module")
def temp_appliance_preconfig_long(request, appliance, pytestconfig):
    """ temp appliance with 24h lease for auth tests """
    with sprout_appliances(
            appliance, config=pytestconfig, preconfigured=True, lease_time=1440,
            provider_type='rhevm'
    ) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliance_preconfig_funcscope_rhevm(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig, preconfigured=True,
            provider_type='rhevm'
    ) as appliances:
        yield appliances[0]


# Single appliance, unconfigured
@pytest.fixture(scope="module")
def temp_appliance_unconfig(temp_appliance_unconfig_modscope):
    yield temp_appliance_unconfig_modscope


@pytest.fixture(scope="module")
def temp_appliance_unconfig_modscope(request, appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=False) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="class")
def temp_appliance_unconfig_clsscope(request, appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=False) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliance_unconfig_funcscope(request, appliance, pytestconfig):
    with sprout_appliances(appliance, config=pytestconfig, preconfigured=False) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliance_unconfig_funcscope_rhevm(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            preconfigured=False,
            provider_type='rhevm'
    ) as appliances:
        yield appliances[0]
        _collect_logs(request.config, appliances)


# Pair of appliances, unconfigured
@pytest.fixture(scope="module")
def temp_appliances_unconfig(temp_appliances_unconfig_modscope):
    yield temp_appliances_unconfig_modscope


@pytest.fixture(scope="module")
def temp_appliances_unconfig_modscope(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False
    ) as appliances:
        yield appliances
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliances_unconfig_funcscope_rhevm(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False,
            provider_type='rhevm'
    ) as appliances:
        yield appliances
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="module")
def temp_appliances_unconfig_modscope_rhevm(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=getattr(request, "param", 2),
            preconfigured=False,
            provider_type='rhevm'
    ) as appliances:
        yield appliances
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliances_preconfig_funcscope(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=True
    ) as appliances:
        yield appliances
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="class")
def temp_appliances_unconfig_clsscope(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False
    ) as appliances:
        yield appliances
        _collect_logs(request.config, appliances)


@pytest.fixture(scope="function")
def temp_appliances_unconfig_funcscope(request, appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=False
    ) as appliances:
        yield appliances


def get_vddk_url(provider):
    try:
        major, minor = str(provider.version).split(".")
    except ValueError:
        major = str(provider.version)
        minor = "0"
    vddk_version = f"v{major}_{minor}"

    try:
        vddk_urls = conf.cfme_data.basic_info.vddk_url
    except (KeyError, AttributeError):
        pytest.skip("VDDK URLs not found in cfme_data.basic_info")

    if vddk_version not in vddk_urls:
        logger.warning("Using VDDK %s, as VDDK %s was unavailable", "v6_5", vddk_version)
        vddk_version = "v6_5"

    url = vddk_urls.get(vddk_version)

    if url is None:
        pytest.skip(f"VDDK {vddk_version} is unavailable, skipping test")

    return url


@pytest.fixture(scope="function")
def configure_fleecing(appliance, provider, setup_provider):
    vddk_url = get_vddk_url(provider)
    provider.setup_hosts_credentials()
    appliance.install_vddk(vddk_url=vddk_url)
    yield
    appliance.uninstall_vddk()
    provider.remove_hosts_credentials()


@pytest.fixture(scope="module")
def configure_fleecing_modscope(appliance, provider, setup_provider_modscope):
    vddk_url = get_vddk_url(provider)
    provider.setup_hosts_credentials()
    appliance.install_vddk(vddk_url=vddk_url)
    yield
    appliance.uninstall_vddk()
    provider.remove_hosts_credentials()


@pytest.fixture(scope="module")
def temp_appliance_extended_db(temp_appliance_preconfig):
    app = temp_appliance_preconfig
    app.evmserverd.stop()
    app.db.extend_partition()
    app.evmserverd.start()
    return app


def _collect_logs(config, appliances):
    """ Wraps calling the pytest_collect_logs hook
    This method is there currently just for saving the typing as the call is
    made on many places.
    """
    config.pluginmanager.hook.pytest_collect_logs(config=config, appliances=appliances)
