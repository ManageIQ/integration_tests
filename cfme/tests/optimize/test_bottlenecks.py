# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from datetime import timedelta

from cfme.optimize.bottlenecks import Bottlenecks
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.timeutil import parsetime
from cfme.utils.ssh import SSHClient


@pytest.fixture(scope="module")
def temp_appliance_extended_db(temp_appliance_preconfig):
    app = temp_appliance_preconfig
    app.evmserverd.stop()
    app.db.extend_partition()
    app.start_evm_service()
    return app


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
    app.evmserverd.stop()
    app.db.drop()
    db_storage_hostname = conf.cfme_data['bottlenecks']['hostname']
    db_storage_ssh = SSHClient(hostname=db_storage_hostname, **conf.credentials['bottlenecks'])
    with db_storage_ssh as ssh_client:
        # Different files for different versions
        ver = "_58" if temp_appliance_extended_db.version > '5.7' else "_57"
        rand_filename = "/tmp/v2_key_{}".format(fauxfactory.gen_alphanumeric())
        ssh_client.get_file("/home/backups/otsuman_db_bottlenecks/v2_key{}".format(ver),
                            rand_filename)
        dump_filename = "/tmp/db_dump_{}".format(fauxfactory.gen_alphanumeric())
        ssh_client.get_file("/home/backups/otsuman_db_bottlenecks/db.backup{}".format(ver),
                            dump_filename)
        region_filename = "/tmp/REGION_{}".format(fauxfactory.gen_alphanumeric())
        ssh_client.get_file("/home/backups/otsuman_db_bottlenecks/REGION{}".format(ver),
                            region_filename)
        guid_filename = "/tmp/GUID_{}".format(fauxfactory.gen_alphanumeric())
        ssh_client.get_file("/home/backups/otsuman_db_bottlenecks/GUID{}".format(ver),
                            guid_filename)

    with app.ssh_client as ssh_client:
        ssh_client.put_file(rand_filename, "/var/www/miq/vmdb/certs/v2_key")
        ssh_client.put_file(dump_filename, "/tmp/evm_db.backup")
        ssh_client.put_file(region_filename, "/var/www/miq/vmdb/REGION")
        ssh_client.put_file(guid_filename, "/var/www/miq/vmdb/GUID")

    app.db.restore()
    app.start_evm_service()
    app.wait_for_web_ui()


@pytest.mark.tier(2)
def test_bottlenecks_report_event_groups(temp_appliance_extended_db, db_restore, db_tbl, db_events):
    """ Checks event_groups selectbox in report tab. It should filter events by type """
    with temp_appliance_extended_db:
        view = navigate_to(Bottlenecks, 'All')
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
    """ Checks host_events checkbox in report tab. It should show or not host events """
    with temp_appliance_extended_db:
        view = navigate_to(Bottlenecks, 'All')
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
    """ Checks time zone selectbox in report tab. It should change time zone of events in table """
    with temp_appliance_extended_db:
        view = navigate_to(Bottlenecks, 'All')
        row = view.report.event_details[0]
        # Selecting row by uniq value
        db_row = db_events.filter(db_tbl.message == row[5].text)
        # Compare bottleneck's table timestamp with db
        assert row[0].text == db_row[0][0].strftime(parsetime.american_with_utc_format)
        # Changing time zone
        view.report.time_zone.fill('(GMT-04:00) La Paz')
        row = view.report.event_details[0]
        assert row[0].text == (db_row[0][0] - timedelta(hours=4)).strftime("%m/%d/%y %H:%M:%S -04")


@pytest.mark.tier(2)
def test_bottlenecks_summary_event_groups(temp_appliance_extended_db, db_restore, db_tbl,
                                          db_events):
    """ Checks event_groups selectbox in summary tab. It should filter events by type """
    with temp_appliance_extended_db:
        view = navigate_to(Bottlenecks, 'All')
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
    """ Checks host_events checkbox in summary tab. It should show or not host events """
    with temp_appliance_extended_db:
        view = navigate_to(Bottlenecks, 'All')
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
    """ Checks time zone selectbox in summary tab. It should change time zone of events in chart """
    with temp_appliance_extended_db:
        view = navigate_to(Bottlenecks, 'All')
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
