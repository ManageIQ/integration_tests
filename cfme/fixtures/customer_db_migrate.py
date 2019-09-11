from os import path as os_path

import pytest

from cfme.utils.appliance import ApplianceException
from cfme.utils.config_data import cfme_data
from cfme.utils.log import logger


@pytest.fixture(scope="module")
def customer_db_migrate(temp_appliance_preconfig):
    app = temp_appliance_preconfig
    app.evmserverd.stop()
    app.db.extend_partition()
    app.evmserverd.start()

    # Download the database
    db_url = cfme_data['db_backups']['MBU_LAB']['url']
    db_desc = cfme_data['db_backups']['MBU_LAB']['desc']
    logger.info("Downloading database: {}".format(db_desc))
    url_basename = os_path.basename(db_url)
    result = app.ssh_client.run_command(
        'curl -o "/{}" "{}"'.format(url_basename, db_url), timeout=30)
    assert result.success, "Failed to download database: {}".format(result.output)

    # Stop EVM service and drop vmdb_production DB
    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    # restore new DB
    result = app.ssh_client.run_command(
        'pg_restore -v --dbname=vmdb_production /{}'.format(url_basename), timeout=600)
    assert result.success, "Failed to restore new database: {}".format(result.output)
    app.db.migrate()
    app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    # start evmserverd, wait for web UI to start and try to log in
    try:
        app.evmserverd.start()
    except ApplianceException:
        result = app.ssh_client.run_rake_command("evm:start")
        assert result.success, "Couldn't start evmserverd: {}".format(result.output)
    app.wait_for_web_ui(timeout=600)
    app.db.reset_user_pass()
    # Disable roles in the UI

    return app
