from datetime import timedelta

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.ssh import SSHClient
from cfme.utils.timeutil import parsetime

pytestmark = [
    test_requirements.bottleneck,
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                            reason='Tests not supported on pod appliance'),
    pytest.mark.ignore_stream('5.11')]


@pytest.fixture(scope="module")
def db_tbl(temp_appliance_extended_db):
    app = temp_appliance_extended_db
    return app.db.client['bottleneck_events']


@pytest.fixture(scope="module")
def db_events(temp_appliance_extended_db, db_tbl):
    app = temp_appliance_extended_db
    return app.db.client.session.query(db_tbl.timestamp,
    db_tbl.resource_type, db_tbl.resource_name, db_tbl.event_type, db_tbl.severity, db_tbl.message)


@pytest.fixture(scope="module")
def db_restore(temp_appliance_extended_db):
    app = temp_appliance_extended_db
    # get app version for backup
    ver = str(temp_appliance_extended_db.version).replace('.', '_')
    ver = ver[:3] if ver[3] == '_' else ver[:4]
    # get DB backup file
    db_storage_hostname = conf.cfme_data.bottlenecks.hostname
    db_storage_ssh = SSHClient(hostname=db_storage_hostname, **conf.credentials.bottlenecks)
    rand_filename = "/tmp/db.backup_{}".format(fauxfactory.gen_alphanumeric())
    db_storage_ssh.get_file("{}/db.backup_{}".format(
        conf.cfme_data.bottlenecks.backup_path, ver), rand_filename)
    app.ssh_client.put_file(rand_filename, "/tmp/evm_db.backup")

    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    app.db.restore()
    # When you load a database from an older version of the application, you always need to
    # run migrations.
    # https://bugzilla.redhat.com/show_bug.cgi?id=1643250
    app.db.migrate()
    app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    app.evmserverd.start()
    app.wait_for_web_ui()


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_bottlenecks_report_event_groups(temp_appliance_extended_db, db_restore, db_tbl, db_events):
    """ Checks event_groups selectbox in report tab. It should filter events by type

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Optimize
    """
    col = temp_appliance_extended_db.collections.bottlenecks
    view = navigate_to(col, 'All')
    # Enabling this option to show all possible values
    view.report.show_host_events.fill(True)
    view.report.event_groups.fill('Capacity')
    rows = view.report.event_details.rows()
    # Compare number of rows in bottleneck's table with number of rows in db
    assert sum(1 for row in rows) == db_events.filter(db_tbl.event_type == 'DiskUsage').count()
    view.report.event_groups.fill('Utilization')
    rows = view.report.event_details.rows()
    assert sum(1 for row in rows) == db_events.filter(db_tbl.event_type != 'DiskUsage').count()


@pytest.mark.tier(2)
def test_bottlenecks_report_show_host_events(temp_appliance_extended_db, db_restore, db_events):
    """ Checks host_events checkbox in report tab. It should show or not host events

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Optimize
    """
    col = temp_appliance_extended_db.collections.bottlenecks
    view = navigate_to(col, 'All')
    view.report.show_host_events.fill(False)
    rows = view.report.event_details.rows(type='Host / Node')
    # Checking that rows with value 'Host / Node' absent in table
    assert not sum(1 for row in rows)
    view.report.show_host_events.fill(True)
    rows = view.report.event_details.rows()
    # Compare number of rows in bottleneck's table with number of rows in db
    assert sum(1 for row in rows) == db_events.count()


@pytest.mark.tier(2)
def test_bottlenecks_report_time_zone(temp_appliance_extended_db, db_restore, db_tbl, db_events):
    """ Checks time zone selectbox in report tab. It should change time zone of events in table

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Optimize
    """
    col = temp_appliance_extended_db.collections.bottlenecks
    view = navigate_to(col, 'All')
    row = view.report.event_details[0]
    # Selecting row by uniq value
    db_row = db_events.filter(db_tbl.message == row[5].text)
    # Compare bottleneck's table timestamp with db
    assert row[0].text == db_row[0][0].strftime(parsetime.american_with_utc_format)
    # Changing time zone
    view.report.time_zone.fill('(GMT-04:00) La Paz')
    row = view.report.event_details[0]
    assert row[0].text == (db_row[0][0] - timedelta(hours=4)).strftime("%m/%d/%y %H:%M:%S -04")


@pytest.mark.meta(blockers=[BZ(1507565, forced_streams=["5.8"])])
@pytest.mark.tier(2)
def test_bottlenecks_summary_event_groups(temp_appliance_extended_db, db_restore, db_tbl,
                                          db_events):
    """ Checks event_groups selectbox in summary tab. It should filter events by type

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Optimize
    """
    col = temp_appliance_extended_db.collections.bottlenecks
    view = navigate_to(col, 'All')
    # Enabling this option to show all possible values
    view.summary.show_host_events.fill(True)
    view.summary.event_groups.fill('Capacity')
    events = view.summary.chart.get_events()
    # Compare number of events in chart with number of rows in db
    assert len(events) == db_events.filter(db_tbl.event_type == 'DiskUsage').count()
    view.summary.event_groups.fill('Utilization')
    events = view.summary.chart.get_events()
    assert len(events) == db_events.filter(db_tbl.event_type != 'DiskUsage').count()


@pytest.mark.tier(2)
def test_bottlenecks_summary_show_host_events(temp_appliance_extended_db, db_restore, db_events):
    """ Checks host_events checkbox in summary tab. It should show or not host events

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Optimize
    """
    col = temp_appliance_extended_db.collections.bottlenecks
    view = navigate_to(col, 'All')
    view.summary.show_host_events.fill(False)
    # Checking that events with value 'Host / Node' absent in table
    events = view.summary.chart.get_events()
    assert not sum(1 for event in events if event.type == 'Host')
    view.summary.show_host_events.fill(True)
    events = view.summary.chart.get_events()
    # Compare number of events in chart with number of rows in db
    assert len(events) == db_events.count()


@pytest.mark.tier(2)
def test_bottlenecks_summary_time_zone(temp_appliance_extended_db, db_restore, db_tbl, db_events):
    """ Checks time zone selectbox in summary tab. It should change time zone of events in chart

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Optimize
    """
    col = temp_appliance_extended_db.collections.bottlenecks
    view = navigate_to(col, 'All')
    events = view.summary.chart.get_events()
    # Selecting row by uniq value
    db_row = db_events.filter(db_tbl.message == events[0].message)
    # Compare event timestamp with db
    assert events[0].time_stamp == db_row[0][0].strftime(parsetime.iso_with_utc_format)
    # Changing time zone
    view.summary.time_zone.fill('(GMT-04:00) La Paz')
    events = view.summary.chart.get_events()
    assert events[0].time_stamp == (db_row[0][0] - timedelta(hours=4)).strftime("%Y-%m-%d "
                                                                                "%H:%M:%S -04")
