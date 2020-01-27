from os import path as os_path

import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.base.ui import navigate_to
from cfme.utils.appliance import ApplianceException
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger

pytestmark = [
    test_requirements.db_migration,
    pytest.mark.uncollectif(lambda appliance: appliance.is_dev,
                            reason="DB migrate tests not valid for dev server")
]


def pytest_generate_tests(metafunc):
    if metafunc.function in {test_upgrade_single_inplace,
                             test_db_migrate_replication,
                             test_upgrade_single_sidebyside}:
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


@pytest.fixture(scope="function")
def temp_appliance_remote(temp_appliance_preconfig_funcscope):
    """Needed for db_migrate_replication as you can't drop a remote db due to subscription"""
    app = temp_appliance_preconfig_funcscope
    app.evmserverd.stop()
    app.db.extend_partition()
    app.evmserverd.start()
    return app


@pytest.fixture(scope="function")
def temp_appliance_global_region(temp_appliance_unconfig_funcscope_rhevm):
    temp_appliance_unconfig_funcscope_rhevm.appliance_console_cli.configure_appliance_internal(
        99, 'localhost', credentials['database']['username'], credentials['database']['password'],
        'vmdb_production', temp_appliance_unconfig_funcscope_rhevm.unpartitioned_disks[0])
    temp_appliance_unconfig_funcscope_rhevm.evmserverd.wait_for_running()
    temp_appliance_unconfig_funcscope_rhevm.wait_for_web_ui()
    return temp_appliance_unconfig_funcscope_rhevm


@pytest.fixture(scope="function")
def appliance_preupdate(temp_appliance_preconfig_funcscope_upgrade, appliance):
    """Reconfigure appliance partitions and adds repo file for upgrade"""
    series = appliance.version.series()
    update_url = "update_url_{}".format(series.replace('.', ''))
    temp_appliance_preconfig_funcscope_upgrade.db.extend_partition()
    urls = cfme_data["basic_info"][update_url]
    temp_appliance_preconfig_funcscope_upgrade.ssh_client.run_command(
        "curl {} -o /etc/yum.repos.d/update.repo".format(urls)
    )
    return temp_appliance_preconfig_funcscope_upgrade


def download_and_migrate_db(app, db_url):
    # Download the database
    logger.info("Downloading database: {}".format(db_url))
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
        app.evmserverd.start()
    except ApplianceException:
        result = app.ssh_client.run_rake_command("evm:start")
        assert result.success, "Couldn't start evmserverd: {}".format(result.output)
    app.wait_for_web_ui(timeout=600)
    app.db.reset_user_pass()
    wait_for(navigate_to, (app.server, 'LoginScreen'), handle_exception=True, timeout='5m')
    app.server.login(app.user)


@pytest.mark.ignore_stream('upstream')
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1734076])
def test_db_migrate(temp_appliance_extended_db, db_url, db_version, db_desc):
    """
    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Appliance
    Bugzilla:
        1734076
    """
    download_and_migrate_db(temp_appliance_extended_db, db_url)


@pytest.mark.parametrize('dbversion',
    ['ec2_5540', 'azure_5620', 'rhev_57', 'scvmm_58', 'vmware_59'],
    ids=['55', '56', '57', '58', '59'])
def test_db_migrate_replication(temp_appliance_remote, dbversion, temp_appliance_global_region):
    """
    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
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
        app.evmserverd.start()
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


# There inplace upgrade to 5.11 is not supported.
@pytest.mark.ignore_stream("5.11")
@pytest.mark.tier(2)
def test_upgrade_single_inplace(appliance_preupdate, appliance):
    """Tests appliance upgrade between streams

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/3h
        testtype: functional
    """
    appliance_preupdate.evmserverd.stop()
    result = appliance_preupdate.ssh_client.run_command('yum update -y', timeout=3600)
    assert result.success, "update failed {}".format(result.output)
    appliance_preupdate.db.migrate()
    appliance_preupdate.db.automate_reset()
    appliance_preupdate.db_service.restart()
    appliance_preupdate.evmserverd.start()
    appliance_preupdate.wait_for_web_ui()
    result = appliance_preupdate.ssh_client.run_command('cat /var/www/miq/vmdb/VERSION')
    assert result.output in appliance.version


@pytest.mark.manual
@test_requirements.update
@test_requirements.db_migration
@pytest.mark.meta(coverage=[1749694, 1735114, 1655794])
def test_upgrade_single_sidebyside():
    """ Test whether an upgrade procedure from CFME 5.x to CFME 5.11 results in
    working environment.

    Note that only the sidebyside upgrade to to CFME 5.11 is supported.

    Note this test is quite similar test_db_migrate and perhaps can be removed
    after the zone checking and ansible checking is implemented there.

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/3h
        startsin: 5.11
        testSteps:
            1. Get CFME VMs of preupgrade and target version.
            2. Make sure the ansible is enabled and create an ansible playbook
               service (for testing the 1735114).
            3. Turn off the evmserverd processes on both.
            4. Dump the DB of the preupgrade appliance.
            5. Restore it on the target version appliance.
            6. Migrate the database.
            7. Check that a zone exists on the target appliance (as there was a bug 1749694)
            8. Check that the service provisioning tab doesn't
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7. Zone exists on the target appliance.
            8. An empty section or a friendly message such as "No Output available"
    Bugzila:
        1749694
        1735114
        1655794
    """
    pass
