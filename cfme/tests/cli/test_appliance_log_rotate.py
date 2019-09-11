import datetime

import dateutil

from cfme import test_requirements


LOGS = ["/var/www/miq/vmdb/log/evm.log",
        "/var/opt/rh/rh-postgresql95/lib/pgsql/data/pg_log/postgresql.log"]


def advance_appliance_date_by_day(appliance):
    """Advance date on the appliance by one day."""
    txt_date = appliance.ssh_client.run_command('date --rfc-3339=ns').output
    appliance_date = dateutil.parser.parse(txt_date)
    td = datetime.timedelta(days=1)
    advanced_txt_date = (appliance_date + td).strftime("%Y-%m-%d %H:%M:%S%z")
    appliance.ssh_client.run_command("date -s '{}'".format(advanced_txt_date))


@test_requirements.appliance
def test_appliance_log_rotate(temp_appliance_preconfig_funcscope):
    """ Checks whether the log is logrotated daily.

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1/12h
        startsin: 5.6
    """
    appliance = temp_appliance_preconfig_funcscope
    assert appliance.ssh_client.run_command("/etc/cron.daily/logrotate").success

    initial_log_files = {}
    for log_path in LOGS:
        initial_log_files[log_path] = appliance.ssh_client.run_command(
            "ls -1 {}*".format(log_path)).output.split('\n')
        appliance.ssh_client.run_command(
            "echo 'Ensure line in logs' >> {}".format(log_path))

    # Perform the logrotate.
    advance_appliance_date_by_day(appliance)
    assert appliance.ssh_client.run_command("/etc/cron.daily/logrotate").success

    for log_path in LOGS:
        adv_time_log_files = appliance.ssh_client.run_command("ls -1 {}*".format(
            log_path)).output.split('\n')
        assert set(initial_log_files[log_path]) < set(adv_time_log_files)
