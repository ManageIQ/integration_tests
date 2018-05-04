import tempfile

import pytest
from os import path as os_path
from wait_for import wait_for

from cfme.base.ui import navigate_to
from cfme.utils import os
from cfme.utils.appliance import ApplianceException
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger
from cfme.utils.repo_gen import process_url, build_file
from cfme.utils.version import get_stream

pytestmark = [pytest.mark.uncollectif(lambda appliance: appliance.is_dev, reason="rails server")]


def pytest_generate_tests(metafunc):
    if metafunc.function in {test_upgrade_single_inplace, test_db_migrate_replication}:
        return

    argnames, argvalues, idlist = ['db_url', 'db_version', 'db_desc'], [], []
    db_backups = cfme_data.get('db_backups', {})
    if not db_backups:
        pytest.skip('No db backup information available!')
    for key, data in db_backups.items():
        # Once we can access the appliance in here, we can do
        # if data.version >= appliance.version or \
        #         get_stream(data.version) == get_stream(appliance.version):
        #     continue
        argvalues.append((data.url, data.version, data.desc))
        idlist.append(key)
    return metafunc.parametrize(argnames=argnames, argvalues=argvalues, ids=idlist)


@pytest.fixture(scope="module")
def temp_appliance_extended_db(temp_appliance_preconfig):
    app = temp_appliance_preconfig
    app.evmserverd.stop()
    app.db.extend_partition()
    app.start_evm_service()
    return app


@pytest.fixture(scope="function")
def temp_appliance_remote(temp_appliance_preconfig_funcscope):
    """Needed for db_migrate_replication as you can't drop a remote db due to subscription"""
    app = temp_appliance_preconfig_funcscope
    app.evmserverd.stop()
    app.db.extend_partition()
    app.start_evm_service()
    return app


@pytest.fixture(scope="function")
def temp_appliance_global_region(temp_appliance_unconfig_funcscope_rhevm):
    temp_appliance_unconfig_funcscope_rhevm.appliance_console_cli.configure_appliance_internal(
        99, 'localhost', credentials['database']['username'], credentials['database']['password'],
        'vmdb_production', temp_appliance_unconfig_funcscope_rhevm.unpartitioned_disks[0])
    temp_appliance_unconfig_funcscope_rhevm.wait_for_evm_service()
    temp_appliance_unconfig_funcscope_rhevm.wait_for_web_ui()
    return temp_appliance_unconfig_funcscope_rhevm


@pytest.fixture(scope="function")
def appliance_preupdate(temp_appliance_preconfig_funcscope_upgrade, appliance):
    """Reconfigure appliance partitions and adds repo file for upgrade"""
    update_url = ('update_url_' + ''.join([i for i in get_stream(appliance.version)
        if i.isdigit()]))
    temp_appliance_preconfig_funcscope_upgrade.db.extend_partition()
    urls = process_url(cfme_data['basic_info'][update_url])
    output = build_file(urls)
    with tempfile.NamedTemporaryFile('w') as f:
        f.write(output)
        f.flush()
        os.fsync(f.fileno())
        temp_appliance_preconfig_funcscope_upgrade.ssh_client.put_file(
            f.name, '/etc/yum.repos.d/update.repo')
    return temp_appliance_preconfig_funcscope_upgrade


@pytest.mark.ignore_stream('5.5', 'upstream')
@pytest.mark.tier(2)
@pytest.mark.meta(
    blockers=[BZ(1354466, unblock=lambda db_url: 'ldap' not in db_url)])
def test_db_migrate(temp_appliance_extended_db, db_url, db_version, db_desc):
    app = temp_appliance_extended_db
    # Download the database
    logger.info("Downloading database: {}".format(db_desc))
    url_basename = os_path.basename(db_url)
    loc = "/tmp/"
    result = app.ssh_client.run_command(
        'curl -o "{}{}" "{}"'.format(loc, url_basename, db_url), timeout=30)
    assert result.success, "Failed to download database: {}".format(result.output)
    # The v2_key is potentially here
    v2key_url = os_path.join(os_path.dirname(db_url), "v2_key")
    # Stop EVM service and drop vmdb_production DB
    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    # restore new DB
    result = app.ssh_client.run_command(
        'pg_restore -v --dbname=vmdb_production {}{}'.format(loc, url_basename), timeout=600)
    assert result.success, "Failed to restore new database: {}".format(result.output)
    app.db.migrate()
    # fetch v2_key
    try:
        result = app.ssh_client.run_command(
            'curl "{}"'.format(v2key_url), timeout=15)
        assert result.success, "Failed to download v2_key: {}".format(result.output)
        assert ":key:" in result.output, "Not a v2_key file: {}".format(result.output)
        result = app.ssh_client.run_command(
            'curl -o "/var/www/miq/vmdb/certs/v2_key" "{}"'.format(v2key_url), timeout=15)
        assert result.success, "Failed to download v2_key: {}".format(result.output)
    # or change all invalid (now unavailable) passwords to 'invalid'
    except AssertionError:
        app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    # start evmserverd, wait for web UI to start and try to log in
    try:
        app.start_evm_service()
    except ApplianceException:
        result = app.ssh_client.run_rake_command("evm:start")
        assert result.success, "Couldn't start evmserverd: {}".format(result.output)
    app.wait_for_web_ui(timeout=600)
    app.db.reset_user_pass()
    wait_for(lambda: navigate_to(app.server, 'LoginScreen'), handle_exception=True)
    app.server.login(app.user)


@pytest.mark.uncollectif(
    lambda appliance, dbversion:
        dbversion in ('scvmm_58', 'ec2_5540') and appliance.version < "5.9")
@pytest.mark.parametrize('dbversion', ['ec2_5540', 'azure_5620', 'rhev_57', 'scvmm_58'],
        ids=['55', '56', '57', '58'])
def test_db_migrate_replication(temp_appliance_remote, dbversion, temp_appliance_global_region):
    app = temp_appliance_remote
    app2 = temp_appliance_global_region
    # Download the database
    logger.info("Downloading database: {}".format(dbversion))
    db_url = cfme_data['db_backups'][dbversion]['url']
    url_basename = os_path.basename(db_url)
    result = app.ssh_client.run_command(
        'curl -o "/tmp/{}" "{}"'.format(url_basename, db_url), timeout=30)
    assert result.success, "Failed to download database: {}".format(result.output)
    # The v2_key is potentially here
    v2key_url = os_path.join(os_path.dirname(db_url), "v2_key")
    # Stop EVM service and drop vmdb_production DB
    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    # restore new DB and migrate it
    result = app.ssh_client.run_command(
        'pg_restore -v --dbname=vmdb_production /tmp/{}'.format(url_basename), timeout=600)
    assert result.success, "Failed to restore new database: {}".format(result.output)
    app.db.migrate()
    # fetch v2_key
    try:
        result = app.ssh_client.run_command(
            'curl "{}"'.format(v2key_url), timeout=15)
        assert result.success, "Failed to download v2_key: {}".format(result.output)
        assert ":key:" in result.output, "Not a v2_key file: {}".format(result.output)
        result = app.ssh_client.run_command(
            'curl -o "/var/www/miq/vmdb/certs/v2_key" "{}"'.format(v2key_url), timeout=15)
        assert result.success, "Failed to download v2_key: {}".format(result.output)
    # or change all invalid (now unavailable) passwords to 'invalid'
    except AssertionError:
        app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    # start evmserverd, wait for web UI to start and try to log in
    try:
        app.start_evm_service()
    except ApplianceException:
        result = app.ssh_client.run_rake_command("evm:start")
        assert result.success, "Couldn't start evmserverd: {}".format(result.output)
    app.wait_for_web_ui(timeout=600)
    # Reset user's password, just in case (necessary for customer DBs)
    app.db.reset_user_pass()
    app.server.login(app.user)

    app.set_pglogical_replication(replication_type=':remote')
    app2.set_pglogical_replication(replication_type=':global')
    app2.add_pglogical_replication_subscription(app.hostname)

    def is_provider_replicated(app, app2):
        return set(app.managed_provider_names) == set(app2.managed_provider_names)
    wait_for(is_provider_replicated, func_args=[app, app2], timeout=30)


def test_upgrade_single_inplace(appliance_preupdate, appliance):
    """Tests appliance upgrade between streams"""
    appliance_preupdate.evmserverd.stop()
    result = appliance_preupdate.ssh_client.run_command('yum update -y', timeout=3600)
    assert result.success, "update failed {}".format(result.output)
    appliance_preupdate.db.migrate()
    appliance_preupdate.db.automate_reset()
    appliance_preupdate.db.restart_db_service()
    appliance_preupdate.start_evm_service()
    appliance_preupdate.wait_for_web_ui()
    assert appliance.version == appliance_preupdate.version
