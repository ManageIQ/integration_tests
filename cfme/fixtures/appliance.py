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

import attr
import pytest

from cfme.test_framework.sprout.client import SproutClient
from cfme.utils import conf
from cfme.utils.log import logger
from cfme.utils.log_validator import FailPatternMatchError
from cfme.utils.log_validator import LogValidator


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

    if config.getoption("update_appliance"):
        for app in apps:
            logger.info("Initiating appliance update on temp appliance ...")
            urls = config.getoption("update_urls")
            app.update_rhel(*urls, reboot=True)
            # Web UI not available on unconfigured appliances
            if preconfigured:
                logger.info("Appliance update finished on temp appliance, waiting for UI ...")
                app.wait_for_web_ui()
            logger.info("Appliance update finished on temp appliance...")

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


@pytest.fixture(scope="module")
def temp_appliance_preconfig_long(appliance, pytestconfig):
    """ temp appliance with 24h lease for auth tests """
    with sprout_appliances(
            appliance, config=pytestconfig, preconfigured=True, lease_time=1440,
            provider_type='rhevm'
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


@pytest.fixture(scope="function")
def temp_appliances_preconfig_funcscope(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=2,
            preconfigured=True
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


def get_vddk_url(provider):
    try:
        major, minor = str(provider.version).split(".")
    except ValueError:
        major = str(provider.version)
        minor = "0"
    vddk_version = "v{}_{}".format(major, minor)

    try:
        vddk_urls = conf.cfme_data.basic_info.vddk_url
    except (KeyError, AttributeError):
        pytest.skip("VDDK URLs not found in cfme_data.basic_info")

    if vddk_version not in vddk_urls:
        logger.warning("Using VDDK %s, as VDDK %s was unavailable", "v6_5", vddk_version)
        vddk_version = "v6_5"

    url = vddk_urls.get(vddk_version)

    if url is None:
        pytest.skip("VDDK {} is unavailable, skipping test".format(vddk_version))

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


@pytest.fixture(scope="function")
def check_evm_log_no_errors():
    @attr.s
    class AppliancesMonitor(object):
        log_validators = attr.ib(factory=list)
        EVM_LOG_PATH = '/var/www/miq/vmdb/log/evm.log'
        EVM_LOG_FAILURE_PATTERNS = ['.* ERROR -- :.*']

        def monitor(self, appliance):
            # TODO don't push to the stack. Do it other way
            with appliance:
                evm_tail = LogValidator(self.EVM_LOG_PATH,
                                        failure_patterns=self.EVM_LOG_FAILURE_PATTERNS)
                evm_tail.start_monitoring()
            self.log_validators.append(evm_tail)

        def multimonitor(self, appliances):
            for a in appliances:
                self.monitor(a)

        def stop_monitoring(self):
            failed = False
            for validator in self.log_validators:
                try:
                    validator.validate()
                except FailPatternMatchError as e:
                    failed = True
                    logger.error("Found ERROR in evm.log: %s", e)
            if failed:
                pytest.fail("There were errors in the evm.log of monitored appliances.")

    am = AppliancesMonitor()
    yield am
    am.stop_monitoring()
