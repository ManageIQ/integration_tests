# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from datetime import timedelta

from cfme.optimize.bottlenecks import Bottlenecks
from cfme.test_framework.sprout.client import SproutClient
from utils import conf
from utils.appliance.implementations.ui import navigate_to
from utils.ssh import SSHClient
from utils.version import current_version


@pytest.yield_fixture(scope="session")
def appliance():
    client = SproutClient.from_config()
    apps, request_id = client.provision_appliances(preconfigured=True)
    yield apps[0]
    client.destroy_pool(request_id)


@pytest.fixture(scope="session")
def db_tbl(appliance):
    return appliance.db['bottleneck_events']


@pytest.fixture(scope="session")
def db_events(appliance, db_tbl):
    return appliance.db.session.query(db_tbl.timestamp,
    db_tbl.resource_type, db_tbl.resource_name, db_tbl.event_type, db_tbl.severity, db_tbl.message)


@pytest.fixture(scope="session")
def extend_db_partition(appliance):
    app = appliance
    app.stop_evm_service()
    app.extend_db_partition()
    app.start_evm_service()


@pytest.fixture(scope="session")
def db_restore(appliance, extend_db_partition):
    app = appliance
    app.stop_evm_service()
    app.drop_database()
    db_storage_hostname = conf.cfme_data['bottlenecks']['hostname']
    db_storage = SSHClient(hostname=db_storage_hostname, **conf.credentials['bottlenecks'])
    with db_storage as ssh:
        # Different files for different versions
        ver = "_56" if current_version() < '5.7' else ""
        rand_filename = "/tmp/v2_key_{}".format(fauxfactory.gen_alphanumeric())
        ssh.get_file("/home/backups/otsuman_db_bottlenecks/v2_key{}".format(ver), rand_filename)
        dump_filename = "/tmp/db_dump_{}".format(fauxfactory.gen_alphanumeric())
        ssh.get_file("/home/backups/otsuman_db_bottlenecks/db.backup{}".format(ver), dump_filename)
        region_filename = "/tmp/REGION_{}".format(fauxfactory.gen_alphanumeric())
        ssh.get_file("/home/backups/otsuman_db_bottlenecks/REGION{}".format(ver), region_filename)
        guid_filename = "/tmp/GUID_{}".format(fauxfactory.gen_alphanumeric())
        ssh.get_file("/home/backups/otsuman_db_bottlenecks/GUID{}".format(ver), guid_filename)

    with app.ssh_client as ssh:
        ssh.put_file(rand_filename, "/var/www/miq/vmdb/certs/v2_key")
        ssh.put_file(dump_filename, "/tmp/evm_db.backup")
        ssh.put_file(region_filename, "/var/www/miq/vmdb/REGION")
        ssh.put_file(guid_filename, "/var/www/miq/vmdb/GUID")

        app.restore_database()
        app.start_evm_service()
        app.wait_for_web_ui()


@pytest.mark.tier(1)
def test_bottlenecks_event_groups(appliance, db_restore, db_tbl, db_events):
    with appliance:
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


@pytest.mark.tier(1)
def test_bottlenecks_show_host_events(appliance, db_restore, db_tbl, db_events):
    with appliance:
        view = navigate_to(Bottlenecks, 'All')
        view.report.show_host_events.fill(False)
        rows = view.report.event_details.rows(type='Host / Node')
        # Checking that rows with value 'Host / Node' absent in table
        assert not sum(1 for row in rows)
        view.report.show_host_events.fill(True)
        rows = view.report.event_details.rows()
        # Compare number of rows in bottleneck's table with number of rows in db
        assert sum(1 for row in rows) == db_events.count()


@pytest.mark.tier(1)
def test_bottlenecks_time_zome(appliance, db_restore, db_tbl, db_events):
    with appliance:
        view = navigate_to(Bottlenecks, 'All')
        row = view.report.event_details[0]
        # Selecting row by uniq value
        db_row = db_events.filter(db_tbl.message == row[5].text)
        # Compare bottleneck's table timestamp with db
        assert row[0].text == db_row[0][0].strftime("%m/%d/%y %H:%M:%S UTC")
        # Changing time zone
        view.report.time_zone.fill('(GMT-04:00) La Paz')
        row = view.report.event_details[0]
        assert row[0].text == (db_row[0][0] - timedelta(hours=4)).strftime("%m/%d/%y %H:%M:%S BOT")
