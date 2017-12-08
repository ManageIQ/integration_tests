import pytest
from os import path as os_path

from cfme.utils.appliance import ApplianceException
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger


@pytest.fixture(scope="module")
def custom_db_migrate(app_creds, temp_appliance_preconfig):
    app = temp_appliance_preconfig
    app.evmserverd.stop()
    app.db.extend_partition()
    app.start_evm_service()

    # Download the database
    db_url = cfme_data['db_backups']['MBU_LAB']['url']
    db_desc = cfme_data['db_backups']['MBU_LAB']['desc']
    logger.info("Downloading database: {}".format(db_desc))
    url_basename = os_path.basename(db_url)
    rc, out = app.ssh_client.run_command(
        'curl -o "/{}" "{}"'.format(url_basename, db_url), timeout=30)
    assert rc == 0, "Failed to download database: {}".format(out)

    # The v2_key is potentially here
    v2key_url = os_path.join(os_path.dirname(db_url), "v2_key")

    # Stop EVM service and drop vmdb_production DB
    app.evmserverd.stop()
    app.db.drop()

    # restore new DB and migrate it
    with app.ssh_client as ssh:
        rc, out = ssh.run_command('createdb vmdb_production', timeout=30)
        assert rc == 0, "Failed to create clean database: {}".format(out)
        rc, out = ssh.run_command(
            'pg_restore -v --dbname=vmdb_production /{}'.format(url_basename), timeout=600)
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
        # fix db password
        rc, out = ssh.run_command("fix_auth --databaseyml -i {}".format(
            app_creds['password']), timeout=45)
        assert rc == 0, "Failed to change invalid password: {}".format(out)
    # start evmserverd, wait for web UI to start and try to log in
    try:
        app.start_evm_service()
    except ApplianceException:
        rc, out = app.ssh_client.run_rake_command("evm:start")
        assert rc == 0, "Couldn't start evmserverd: {}".format(out)
    app.wait_for_web_ui(timeout=600)
    # Reset user's password, just in case (necessary for customer DBs)
    rc, out = ssh.run_rails_command(
        '"u = User.find_by_userid(\'admin\'); u.password = \'{}\'; u.save!"'
        .format(app.user.credential.secret))
    assert rc == 0, "Failed to change UI password of {} to {}:" \
                    .format(app.user.credential.principal, app.user.credential.secret, out)
    app.server.login(app.user)
    # Disable roles in the UI

    return app