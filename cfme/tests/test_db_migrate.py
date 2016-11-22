import pytest
from os import path as os_path

from cfme.login import login
from utils import db, version
from utils.appliance import ApplianceException
from utils.blockers import BZ
from utils.conf import cfme_data
from utils.log import logger
from utils.wait import wait_for


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = ['db_url', 'db_version', 'db_desc'], [], []
    db_backups = cfme_data.get('db_backups', {})
    if not db_backups:
        return []
    for key, data in db_backups.iteritems():
        argvalues.append((data.url, data.version, data.desc))
        idlist.append(key)
    return metafunc.parametrize(argnames=argnames, argvalues=argvalues, ids=idlist)


@pytest.fixture(scope="function")
def stabilize_current_appliance():
    app = pytest.store.current_appliance
    app.reboot(wait_for_web_ui=False)
    app.stop_evm_service()


@pytest.mark.ignore_stream('5.5', 'upstream')
@pytest.mark.tier(2)
@pytest.mark.uncollectif(
    lambda db_version:
        db_version >= version.current_version() or
        version.get_stream(db_version) == version.current_stream())
@pytest.mark.meta(
    blockers=[BZ(1354466, unblock=lambda db_url: 'ldap' not in db_url)])
def test_db_migrate(stabilize_current_appliance, db_url, db_version, db_desc):
    """ This is a destructive test - it _will_ destroy your database """
    app = pytest.store.current_appliance

    # Download the database
    logger.info("Downloading database: {}".format(db_desc))
    url_basename = os_path.basename(db_url)
    rc, out = app.ssh_client.run_command(
        'curl -o "/tmp/{}" "{}"'.format(url_basename, db_url), timeout=30)
    assert rc == 0, "Failed to download database: {}".format(out)

    # The v2_key is potentially here
    v2key_url = os_path.join(os_path.dirname(db_url), "v2_key")

    # wait 30sec until evmserverd is down
    wait_for(app.is_evm_service_running, num_sec=30, fail_condition=True, delay=5,
        message="Failed to stop evmserverd in 30 seconds")

    # restart postgres to clear connections, remove old DB, restore it and migrate it
    with app.ssh_client as ssh:
        def _db_dropped():
            rc, out = ssh.run_command(
                'systemctl restart {}-postgresql'.format(db.scl_name()), timeout=60)
            assert rc == 0, "Failed to restart postgres service: {}".format(out)
            ssh.run_command('dropdb vmdb_production', timeout=15)
            rc, out = ssh.run_command("psql -l | grep vmdb_production | wc -l", timeout=15)
            return rc == 0
        wait_for(_db_dropped, delay=5, timeout=60, message="drop the vmdb_production DB")

        rc, out = ssh.run_command('createdb vmdb_production', timeout=30)
        assert rc == 0, "Failed to create clean database: {}".format(out)
        rc, out = ssh.run_command(
            'pg_restore -v --dbname=vmdb_production /tmp/{}'.format(url_basename), timeout=600)
        assert rc == 0, "Failed to restore new database: {}".format(out)
        rc, out = ssh.run_rake_command("db:migrate", timeout=300)
        assert rc == 0, "Failed to migrate new database: {}".format(out)
        rc, out = ssh.run_rake_command(
            'db:migrate:status 2>/dev/null | grep "^\s*down"', timeout=30)
        assert rc != 0, "Migration failed; migrations in 'down' state found: {}".format(out)
        # fetch GUID and REGION from the DB and use it to replace data in /var/www/miq/vmdb/GUID
        # and /var/www/miq/vmdb/REGION respectively
        data_query = {
            'guid': 'select guid from miq_servers',
            'region': 'select region from miq_regions'
        }
        for data_type, db_query in data_query.items():
            data_filepath = '/var/www/miq/vmdb/{}'.format(data_type.upper())
            rc, out = ssh.run_command(
                'psql -d vmdb_production -t -c "{}"'.format(db_query), timeout=15)
            assert rc == 0, "Failed to fetch {}: {}".format(data_type, out)
            db_data = out.strip()
            assert db_data, "No {} found in database; query '{}' returned no records".format(
                data_type, db_query)
            rc, out = ssh.run_command(
                "echo -n '{}' > {}".format(db_data, data_filepath), timeout=15)
            assert rc == 0, "Failed to replace data in {} with '{}': {}".format(
                data_filepath, db_data, out)
        # fetch v2_key
        try:
            rc, out = ssh.run_command(
                'curl "{}"'.format(v2key_url), timeout=15)
            assert rc == 0, "Failed to download v2_key: {}".format(out)
            assert ":key:" in out, "Not a v2_key file: {}".format(out)
            rc, out = ssh.run_command(
                'curl -o "/var/www/miq/vmdb/certs/v2_key" "{}"'.format(v2key_url), timeout=15)
            assert rc == 0, "Failed to download v2_key: {}".format(out)
        # or change all invalid (now unavailable) passwords to 'invalid'
        except AssertionError:
            rc, out = ssh.run_command("fix_auth -i invalid", timeout=45)
            assert rc == 0, "Failed to change invalid passwords: {}".format(out)
    # start evmserverd, wait for web UI to start and try to log in
    try:
        app.start_evm_service()
    except ApplianceException:
        rc, out = app.ssh_client.run_rake_command("evm:start")
        raise rc == 0, "Couldn't start evmserverd: {}".format(out)
    app.wait_for_web_ui(timeout=600)
    # Reset user's password, just in case (necessary for customer DBs)
    rc, out = ssh.run_rails_command(
        '"u = User.find_by_userid(\'admin\'); u.password = \'{}\'; u.save!"'
        .format(app.user.credential.secret))
    assert rc == 0, "Failed to change UI password of {} to {}:" \
                    .format(app.user.credential.principal, app.user.credential.secret, out)
    login(app.user)
