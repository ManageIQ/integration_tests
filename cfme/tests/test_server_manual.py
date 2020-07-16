"""Manual tests"""
import pytest


pytestmark = [pytest.mark.ignore_stream('upstream'), pytest.mark.manual]


def test_appliance_terminates_unresponsive_worker_process():
    """
    If a queue message consumes significant memory and takes longer than
    the 10 minute queue timeout, the appliance will kill the worker after
    the stopping_timeout.
    Steps to test (see BZ below, comments 30 and 31).

    Bugzilla:
        1395736

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


def test_session_purging_occurs_only_when_session_store_is_sql():
    """
    If Settings > server > session_store is set to "sql", then evm.log
    shows that the Session.check_session_timeout worker gets regularly
    queued (at a regular interval of Settings > workers > worker_base >
    schedule_worker > session_timeout_interval). If session_store is not
    set to "sql", then the worker does not get scheduled.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(1)
def test_pg_stat_activity_view_in_postgres_should_show_worker_information():
    """
    pg_stat_activity view in postgres should show worker information.
    Bug 1445928 - It is impossible to identify the source
    process/appliance for each connection in pg_stat_activity

    Bugzilla:
        1445928

    # su - postgres
    # psql vmdb_production
    vmdb_production=# select pid, application_name from pg_stat_activity;
    pid  |                        application_name
    -------+--------------------------------------------------------------
    ---
    17109 | MIQ 16946 Server[2], default[2]
    17274 | MIQ 17236 Generic[49], s[2], default[2]
    17264 | MIQ 17227 Generic[48], s[2], default[2]
    17286 | MIQ 17266 Schedule[52], s[2], default[2]
    17277 | MIQ 17245 Priority[50], s[2], default[2]
    17280 | MIQ 17254 Priority[51], s[2], default[2]
    17320 | MIQ 17298 Redhat::InfraManager::MetricsCollector[53], s[2],
    d..
    17329 | MIQ 17307 Redhat::InfraManager::MetricsCollector[54], s[2],
    d..
    [...]

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/10h
        startsin: 5.7
    """
    pass


@pytest.mark.tier(1)
def test_verify_purging_of_old_records():
    """
    Verify that DriftState, MiqReportResult, EventStream, PolicyEvent,
    VmdbMetric, Metric, and Container-related records are purged
    regularly.
    Bug 1348625 - We might not be purging all tables that we should be

    Bugzilla:
        1348625

    [----] I, [2017-05-19T07:48:23.994536 #63471:985134]  INFO -- :
    MIQ(DriftState.purge_by_date) Purging Drift states older than
    [2016-11-20 11:48:20 UTC]...Complete - Deleted 0 records"
    [----] I, [2017-09-21T06:09:57.911327 #1775:a53138]  INFO -- :
    MIQ(MiqReportResult.atStartup) Purging adhoc report results...
    complete
    [----] I, [2017-09-21T06:15:31.118400 #2181:a53138]  INFO -- :
    MIQ(EventStream.purge) Purging all events older than [2017-03-25
    10:15:27 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T06:15:31.284846 #2181:a53138]  INFO -- :
    MIQ(PolicyEvent.purge_by_date) Purging Policy events older than
    [2017-03-25 10:15:31 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T06:50:25.643198 #2116:a53138]  INFO -- :
    MIQ(VmdbMetric.purge_by_date) Purging hourly metrics older than
    [2017-03-25 10:50:19 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T06:50:25.674445 #2116:a53138]  INFO -- :
    MIQ(VmdbMetric.purge_by_date) Purging daily metrics older than
    [2017-03-25 10:50:19 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T11:04:18.496532 #32143:a53138]  INFO -- :
    MIQ(Metric::Purging.purge) Purging all realtime metrics older than
    [2017-09-21 11:04:13 UTC]...Complete - Deleted 135 records and 0
    associated tag values - Timings: {:purge_metrics=>0.23389387130737305,
    :total_time=>0.23413729667663574}
    [----] I, [2017-09-27T15:37:42.206807 #6336:39d140]  INFO -- :
    MIQ(Container.purge_by_date) Purging Containers older than [2017-03-31
    19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.264940 #6326:39d140]  INFO -- :
    MIQ(ContainerGroup.purge_by_date) Purging Container groups older than
    [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.281474 #6336:39d140]  INFO -- :
    MIQ(ContainerImage.purge_by_date) Purging Container images older than
    [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.340960 #6336:39d140]  INFO -- :
    MIQ(ContainerDefinition.purge_by_date) Purging Container definitions
    older than [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.392486 #6326:39d140]  INFO -- :
    MIQ(ContainerProject.purge_by_date) Purging Container projects older
    than [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.tier(1)
def test_verify_that_errored_out_queue_messages_are_removed():
    """
    Verify that errored-out queue messages are removed.
    Bug 1460263 - shutdown_and_exit messages get marked as error and never
    removed from miq_queue table

    Bugzilla:
        1460263

    # appliance_console
    -> Stop EVM Server Processes
    -> Start EVM Server Processes
    # cd /var/www/miq/vmdb/
    # bin/rails c
    irb(main):001:0> MiqQueue.where(:state => "error")

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/15h
    """
    pass


@pytest.mark.tier(1)
def test_active_tasks_get_timed_out_when_they_run_too_long():
    """
    active tasks get timed out when they run too long
    Bug 1397600 - After killing reporting worker, report status still says
    Running

    Bugzilla:
        1397600

    ****
    1.) Set task timeout check frequency and timeout values:
    :task_timeout_check_frequency: 600
    :active_task_timeout: 10.minutes
    2.) Queue a bunch of reports.
    3.) Kill the MiqReportingWorker pid(s).
    4.) Repeat #2 and #3 a couple times, until one of the reports gets
    stuck with a Running status.
    5.) After ~10 minutes, see entries like the following in evm.log, and
    verify that the reports show a status of Error in the web UI.
    [----] I, [2017-06-12T16:05:14.491076 #18861:3bd134]  INFO -- :
    MIQ(MiqTask#update_status) Task: [213] [Finished] [Error] [Task [213]
    timed out - not active for more than 600 seconds]
    ****

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.7
    """
    pass


@pytest.mark.tier(1)
def test_verify_benchmark_timings_are_correct():
    """
    Bug 1424716 - Benchmark timings are incorrect for all workers in
    evm.log
    Timings logged in evm.log are/seem to be reasonable values:
    [----] I, [2017-09-21T14:53:01.220711 #23936:ded140]  INFO -- :
    MIQ(ManageIQ::Providers::Vmware::InfraManager::Refresher#refresh) EMS:
    [vsphere6], id: [2]
    Refreshing targets for EMS...Complete - Timings
    {:get_ems_data=>0.11566829681396484,
    :get_vc_data=>0.7215437889099121,
    :get_vc_data_ems_customization_specs=>0.014485597610473633,
    :filter_vc_data=>0.0004775524139404297,
    :get_vc_data_host_scsi=>0.5094377994537354,
    :collect_inventory_for_targets=>1.363351821899414,
    :parse_vc_data=>0.10647010803222656,
    :parse_targeted_inventory=>0.10663747787475586,
    :db_save_inventory=>9.141719341278076,
    :save_inventory=>9.141741275787354,
    :ems_refresh=>10.612204551696777}

    Bugzilla:
        1424716

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass
