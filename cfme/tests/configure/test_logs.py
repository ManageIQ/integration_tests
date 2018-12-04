# -*- coding: utf-8 -*-
import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider(
        [AzureProvider, EC2Provider, RHEVMProvider, SCVMMProvider], scope="module"
    ),
    pytest.mark.usefixtures("setup_provider"),
]


@pytest.fixture
def log_exists(appliance, provider):
    log_exists = bool(
        appliance.ssh_client.run_command(
            "(ls /var/www/miq/vmdb/log/{}.log >> /dev/null 2>&1 && echo True) || echo False".format(
                provider.log_name
            )
        ).output
    )
    return log_exists


def test_provider_log_exists(log_exists):
    """
    Tests if provider log exists

    Metadata:
        test_flag: log

    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    assert log_exists


def test_provider_log_rotate(appliance, provider, log_exists):
    """
    Tests that log rotation works for provider log

    Steps:
    1. Force log rotation with default config miq_logs.conf
    2. Verify that new

    Metadata:
        test_flag: log

    Polarion:
        assignee: None
        initialEstimate: None
    """
    assert log_exists, "Log file {}.log doesn't exist".format(provider.log_name)
    appliance.ssh_client.run_command("logrotate -f /etc/logrotate.d/miq_logs.conf")
    logs_count = int(appliance.ssh_client.run_command(
        "ls -l /var/www/miq/vmdb/log/{}.log*|wc -l".format(
            provider.log_name
        )
    ).output.rstrip())
    assert logs_count > 1, "{}.log wasn't rotated by default miq_logs.conf".format(
        provider.log_name
    )


def test_provider_log_updated(appliance, provider, log_exists):
    """
    Tests that providers log is not empty and updatable

    Steps:
    1. Store log before provider refresh
    2. Refresh provider
    3. Store log once again
    4. Compare logs from 1 and 3

    Metadata:
        test_flag: log

    Polarion:
        assignee: None
        initialEstimate: None
    """
    assert log_exists, "Log file {}.log doesn't exist".format(provider.log_name)
    log_before = appliance.ssh_client.run_command(
        "md5sum /var/www/miq/vmdb/log/{}.log | awk '{{ print $1 }}'".format(
            provider.log_name
        )
    ).output

    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    log_after = appliance.ssh_client.run_command(
        "md5sum /var/www/miq/vmdb/log/{}.log | awk '{{ print $1 }}'".format(
            provider.log_name
        )
    ).output
    assert log_before != log_after, "Log hashes are the same"


@pytest.mark.meta(blockers=[BZ(1633656,
                               unblock=lambda provider: provider.one_of(AzureProvider, EC2Provider),
                               forced_streams=["5.9", "5.10", "upstream"]),
                            BZ(1640718,
                               unblock=lambda provider: not provider.one_of(AzureProvider),
                               forced_streams=["5.9"])
                            ]
                  )
def test_provider_log_level(appliance, provider, log_exists):
    """
    Tests that log level in advanced settings affects log files

    Steps:
    1. Change log level to debug
    2. Refresh provider
    3. Check logs contain debug level
    4. Reset level back

    Metadata:
        test_flag: log

    Polarion:
        assignee: None
        initialEstimate: None
    """
    assert log_exists, "Log file {}.log doesn't exist".format(provider.log_name)
    log_level = appliance.server.advanced_settings['log']['level_{}'.format(provider.log_name)]
    # set log level to debug
    wait_for(lambda: appliance.server.update_advanced_settings(
        {'log': {'level_{}'.format(provider.log_name): 'debug'}}), timeout=300)
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    debug_in_logs = appliance.ssh_client.run_command(
        "cat /var/www/miq/vmdb/log/{}.log | grep DEBUG".format(provider.log_name))
    # set log level back
    appliance.server.update_advanced_settings(
        {'log': {'level_{}'.format(provider.log_name): log_level}})
    assert debug_in_logs.success
