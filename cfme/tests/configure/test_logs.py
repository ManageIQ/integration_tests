import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.log_validator import FailPatternMatchError
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.log_depot,
    pytest.mark.provider(
        [AzureProvider, EC2Provider, RHEVMProvider, SCVMMProvider], scope="module"
    ),
    pytest.mark.usefixtures("setup_provider_modscope"),
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
        assignee: jhenner
        casecomponent: Configuration
        initialEstimate: 1/4h
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
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Configuration
    """
    assert log_exists, f"Log file {provider.log_name}.log doesn't exist"
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
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Configuration
    """
    assert log_exists, f"Log file {provider.log_name}.log doesn't exist"
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


def test_provider_log_level(appliance, provider, log_exists):
    """
    Tests that log level in advanced settings affects log files

    Bugzilla:
        1633656
        1640718

    Metadata:
        test_flag: log

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Configuration
        testSteps:
            1. Change log level to info
            2. Refresh provider
            3. Check logs do contain info messages
            4. Change log level to warn
            5. Refresh provider
            6. Check there are no info messages in the log
            7. Reset log level back
    """
    assert log_exists, f"Log file {provider.log_name}.log doesn't exist"
    log_level = appliance.server.advanced_settings['log'][f'level_{provider.log_name}']
    log = f'/var/www/miq/vmdb/log/{provider.log_name}.log'
    # set log level to info
    wait_for(lambda: appliance.server.update_advanced_settings(
        {'log': {f'level_{provider.log_name}': 'info'}}), timeout=300)
    lv_info = LogValidator(log, matched_patterns=['.*INFO.*'], failure_patterns=['.*DEBUG.*'])
    lv_info.start_monitoring()
    provider.refresh_provider_relationships(wait=600)
    assert lv_info.validate(wait="60s")

    # set log level to warn
    wait_for(lambda: appliance.server.update_advanced_settings(
        {'log': {f'level_{provider.log_name}': 'warn'}}), timeout=300)
    lv = LogValidator(log, failure_patterns=['.*INFO.*'])

    def _no_info():
        lv.start_monitoring()
        provider.refresh_provider_relationships(wait=600)
        try:
            assert lv.validate()
        except FailPatternMatchError:
            return False

    # after changing the log level it doesn't take effect immediately, so might require 1-2 extra
    # times to make sure there are no unwanted messages (from before the log change)
    wait_for(_no_info, num_sec=900, delay=40, message="no INFOs in the log")
    # set log level back
    appliance.server.update_advanced_settings(
        {'log': {f'level_{provider.log_name}': log_level}})
