import pytest
import pytz
from dateutil import parser

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log_validator import LogValidator


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda appliance: appliance.version < '5.9')
def test_configure_vmdb_last_start_time(appliance):
    """
        Go to Settings -> Configure -> Database
        Compare Vmdb Last Start Time with output of command
        "journalctl -u rh-postgresql{}-postgresql.service  --boot=0 | sed '4!d'"

    Polarion:
        assignee: mmojzis
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
    """

    view = navigate_to(appliance.server, 'DatabaseSummary')

    for item in view.summary('Properties').get_text_of('Data Directory').split('/'):
        if 'rh-postgresql' in item:
            logs_last_start_time = appliance.ssh_client.run_command(
                "journalctl -u {}-postgresql.service  --boot=0 | sed '4!d'".format(item))

    ui_last_start_time = parser.parse(view.summary('Properties').get_text_of('Last Start Time'))
    # timedatectl is used here as we will get full timezone name, like 'US/Eastern',
    #  which is easier and safer(to omit UnknownTimeZoneError) to use later
    tz = pytz.timezone(appliance.ssh_client.run_command("timedatectl | grep 'Time zone'")
                       .output.strip().split(' ')[2])
    ui_last_start_updated = ui_last_start_time.replace(
        tzinfo=ui_last_start_time.tzinfo).astimezone(tz)
    assert ui_last_start_updated.strftime('%Y-%m-%d %H:%M:%S %Z') in logs_last_start_time.output


@pytest.mark.tier(1)
def test_configuration_database_garbage_collection(appliance):
    """
        Navigate to Settings -> Configuration -> Diagnostics -> CFME Region -> Database
        Submit Run database Garbage Collection Now a check UI/logs for errors.

    Polarion:
        assignee: mmojzis
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
    """
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=[
                                '.*Queued the action: \[Database GC\] being run for user:.*'],
                            failure_patterns=['.*ERROR.*'])
    evm_tail.fix_before_start()
    view = navigate_to(appliance.server.zone.region, 'Database')
    view.submit_db_garbage_collection_button.click()
    view.flash.assert_message('Database Garbage Collection successfully initiated')
    evm_tail.validate_logs()
