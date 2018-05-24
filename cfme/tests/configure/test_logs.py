# -*- coding: utf-8 -*-
import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([AzureProvider, EC2Provider, RHEVMProvider, SCVMMProvider],
                         scope='module'),
    pytest.mark.usefixtures('setup_provider'),
]

# Provider type - provider log name
provider_log = {'azure': 'azure',
                'ec2': 'aws',
                'scvmm': 'scvmm',
                'rhevm': 'rhevm'}


@pytest.fixture
def log_exists(appliance, provider):
    log_exists = bool(appliance.ssh_client.run_command(
        '(ls /var/www/miq/vmdb/log/{}.log >> /dev/null 2>&1 && echo True) || echo False'.format(
            provider_log[provider.type])).output)
    return log_exists


def test_provider_log_exists(log_exists):
    """
    Tests if provider log exists
    """
    assert log_exists


def test_provider_log_rotate(appliance, provider, log_exists):
    """
    Tests that log rotation works for provider log

    Steps:
    1. Force log rotation with default config miq_logs.conf
    2. Verify that new
    """
    if log_exists:
        appliance.ssh_client.run_command('logrotate -f /etc/logrotate.d/miq_logs.conf')
        logs_count = appliance.ssh_client.run_command(
            'ls -l /var/www/miq/vmdb/log/{}.log*|wc -l'.format(provider_log[provider.type])).output
        assert logs_count > 1, "{}.log wasn't rotated by default miq_logs.conf".format(
            provider_log[provider.type])


def test_provider_log_updated(appliance, provider, log_exists):
    """
    Tests that providers log is not empty and updatable

    Steps:
    1. Store log before provider refresh
    2. Refresh provider
    3. Store log once again
    4. Compare logs from 1 and 3
    """
    if log_exists:
        log_before = appliance.ssh_client.run_command(
            "md5sum /var/www/miq/vmdb/log/{}.log | awk '{{ print $1 }}'".format(
                provider_log[provider.type])).output

        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        log_after = appliance.ssh_client.run_command(
            "md5sum /var/www/miq/vmdb/log/{}.log | awk '{{ print $1 }}'".format(
                provider_log[provider.type])).output
        assert log_before != log_after, "Log hashes are the same"
