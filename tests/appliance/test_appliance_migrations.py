# -*- coding: utf-8 -*-

import pytest
import subprocess as sub
from fixtures import navigation as nav
from utils.appliance import provision_appliance
from utils.conf import cfme_data, migration_tests
from utils.log import logger
from utils.providers import setup_provider


""" This test suite focuses on running through restoring databases from older versions of EVM/CFME
and running though the db migrations to allow the old data to be run on the latest versions of the
CFME.

Tests are defined within migration_tests.yaml like so:
        backup_tests:
            fancy_name:
                url: "http://server.lab.com/backups/miq_dumpall_vmdb_production_20121017_135354.gz"
                counts:
                    table_one: 1
                    table_two: 2
            db_test_two:
                url: "http://server.lab.com/backups/miq_dumpall_vmdb_production_20130130_115245.gz"
                counts:
                    table_one: 1
                    table_two: 2

The following are also used for provisioning a appliance with a template containing a second disk
for the appliance database that is adequate for any restores that you may want to do as well as
pointers to the scripts involved with restoring.
        basic_info:
            appliances_provider: vsphere5
            appliance_template_big_db_disk: cfme-5221-0221-ldb
            restore_scripts_url: http://server.lab.com/backups/restore_scripts_20131206_0.tgz
"""


def nav_to_roles():
    """ Helper nav function to get to server settings """
    # Nav to the settings tab
    settings_pg = nav.cnf_configuration_pg().click_on_settings()
    # Workaround to rudely bypass a popup that sometimes appears for
    # unknown reasons.
    # See also: https://github.com/RedHatQE/cfme_tests/issues/168
    from pages.configuration_subpages.settings_subpages.server_settings import ServerSettings
    server_settings_pg = ServerSettings(settings_pg.testsetup)
    # sst is a configuration_subpages.settings_subpages.server_settings_subpages.
    #   server_settings_tab.ServerSettingsTab
    return server_settings_pg.click_on_server_tab()


def pytest_generate_tests(metafunc):
    """ Test generator """
    global test_list
    argnames = ['backups', 'backup_test']
    tests = []
    for backup_test in migration_tests.get('backup_tests', []):
        tests.append(['', backup_test])
    metafunc.parametrize(argnames, tests, scope="module")


@pytest.mark.usefixtures("backups")
@pytest.mark.long_running
class TestSingleApplianceMigration():

    def test_app_migration(self, backup_test, soft_assert):
        vm_name = "migtest_" + backup_test
        provider = cfme_data["basic_info"]["appliances_provider"]
        test_data = migration_tests["backup_tests"][backup_test]
        template = cfme_data['basic_info']['appliance_template_big_db_disk']

        # provision appliance and configure
        appliance = provision_appliance(
            vm_name_prefix=vm_name, template=template, provider_name=provider)
        logger.info("appliance IP address: " + str(appliance.address))
        appliance.enable_internal_db()
        appliance.wait_for_web_ui()

        # start restore and migration
        appliance_ssh = appliance.ssh_client()
        appliance_ssh.put_file("./scripts/restore.py", "/root")
        appliance_ssh.run_command("curl -o restore_scripts.gz " +
            cfme_data["basic_info"]["restore_scripts_url"])
        if "restore_fixes_url" in cfme_data["basic_info"].keys():
            appliance_ssh.run_command("curl -o fix_scripts.gz " +
                cfme_data["basic_info"]["restore_fixes_url"])
        appliance_ssh.run_command("curl -o backup.gz " + test_data['url'])
        logger.info("Running db restore/migration...")
        rc, output = appliance_ssh.run_command("/root/restore.py --scripts " +
            "/root/restore_scripts.gz --backupfile /root/backup.gz")
        soft_assert(rc == 0)

        # re-init the connection, times out over long migrations
        appliance_ssh.close()
        appliance_ssh = appliance.ssh_client()
        appliance_ssh.get_file("/root/output.log", ".")

        # Log the restore/migration output
        process = sub.Popen("cat ./output.log; rm -rf ./output.log",
            shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        output, error = process.communicate()
        logger.info("Running cmd:   cat ./output.log; rm -rf ./output.log")
        logger.info("Output: \n" + output)

        # get database table counts
        this_db = appliance.db
        session = this_db.session
        logger.info("Checking db table counts after migration...")
        db_counts = {}
        for table_name in sorted(test_data['counts'].keys()):
            db_counts[table_name] = session.query(this_db[table_name]).count()

        # start up evmserverd and poke ui
        appliance_ssh.run_command("service evmserverd start")
        appliance.wait_for_web_ui()
        with appliance.browser_session():
            nav.home_page_logged_in()
            nav_to_roles().edit_current_role_list("ems_inventory ems_operations")
            setup_provider(provider)
            provider_details = nav.infra_providers_pg().load_provider_details(
                cfme_data["management_systems"][provider]["name"])
            vm_details = provider_details.all_vms().find_vm_page(
                appliance.vm_name, None, False, True, 6)
            soft_assert(vm_details.on_vm_details(appliance.vm_name))

        # check table counts vs what we are expecting
        for table_name in sorted(test_data['counts'].keys()):
            expected_count = test_data['counts'][table_name]
            actual_count = db_counts[table_name]
            soft_assert(actual_count == expected_count, 'Table ' + table_name + '(' +
                str(actual_count) + ') not matching expected(' + str(expected_count) + ')')

        # delete appliance
        logger.info("Delete provisioned appliance: " + appliance.address)
        appliance.destroy()
