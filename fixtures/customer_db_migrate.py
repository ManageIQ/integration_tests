import pytest
from os import path as os_path

from cfme.utils.appliance import ApplianceException
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger


@pytest.fixture(scope="module")
def customer_db_migrate(temp_appliance_preconfig):
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

    # Stop EVM service and drop vmdb_production DB
    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    # restore new DB
    rc, out = app.ssh_client.run_command(
        'pg_restore -v --dbname=vmdb_production /{}'.format(url_basename), timeout=600)
    assert rc == 0, "Failed to restore new database: {}".format(out)
    app.db.migrate()
    app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    # start evmserverd, wait for web UI to start and try to log in
    try:
        app.start_evm_service()
    except ApplianceException:
        rc, out = app.ssh_client.run_rake_command("evm:start")
        assert rc == 0, "Couldn't start evmserverd: {}".format(out)
    app.wait_for_web_ui(timeout=600)
    app.reset_user_pass()
    # Disable roles in the UI

    return app
