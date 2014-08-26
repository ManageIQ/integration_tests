# -*- coding: utf-8 -*-

import pytest
import time
import subprocess as sub
from utils.appliance import provision_appliance
from utils.conf import cfme_data, migration_tests
from utils.log import logger
from utils.providers import setup_provider
from cfme.configure.configuration import set_server_roles, get_server_roles
from cfme.infrastructure.provider import get_from_config as get_infra_provider
from cfme.infrastructure.virtual_machines import Vm


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


def pytest_generate_tests(metafunc):
    """ Test generator """
    global test_list
    argnames = ['backups', 'backup_test']
    tests = []
    new_idlist = []
    for backup_test in migration_tests.get('backup_tests'):
        tests.append(['', backup_test])
        new_idlist.append(backup_test)
    metafunc.parametrize(argnames, tests, ids=new_idlist, scope="module")


@pytest.yield_fixture()
def this_appliance(backup_test):
    vm_name = "tst_migration_" + backup_test
    provider = cfme_data["basic_info"]["appliances_provider"]
    template = cfme_data['basic_info']['appliance_template_big_db_disk']

    # provision appliance and configure
    appliance = provision_appliance(
        vm_name_prefix=vm_name, template=template, provider_name=provider)
    logger.info("appliance IP address: " + str(appliance.address))
    appliance.enable_internal_db()
    appliance.wait_for_web_ui(timeout=900)

    yield appliance

    # delete appliance
    logger.info("Delete provisioned appliance: " + appliance.address)
    #appliance.destroy()


@pytest.mark.usefixtures("backups")
@pytest.mark.long_running
class TestSingleApplianceMigration():

    def test_app_migration(self, backup_test, this_appliance, soft_assert):

        test_data = migration_tests["backup_tests"][backup_test]
        provider = cfme_data["basic_info"]["appliances_provider"]

        # start restore and migration
        appliance_ssh = this_appliance.ssh_client()
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
        appliance_ssh = this_appliance.ssh_client()
        rc, output = appliance_ssh.run_command("gzip -c /root/output.log > /root/" + backup_test + "_output.gz")
        appliance_ssh.get_file("/root/" + backup_test + "_output.gz", ".")

        # get database table counts
        this_db = this_appliance.db
        session = this_db.session
        logger.info("Checking db table counts after migration...")
        db_counts = {}
        for table_name in sorted(test_data['counts'].keys()):
            db_counts[table_name] = session.query(this_db[table_name]).count()

        # start up evmserverd and poke ui
        appliance_ssh.run_command("service evmserverd start")
        this_appliance.wait_for_web_ui()
        time.sleep(120)   # seeing some flakiness when adjusting roles too quick
        with this_appliance.browser_session():
            pytest.sel.force_navigate('dashboard')
            roles = get_server_roles()
            roles["ems_inventory"] = True
            roles["ems_operations"] = True
            set_server_roles(**roles)
            provider_crud = get_infra_provider(provider)
            setup_provider(provider)
            vm = Vm(this_appliance.vm_name, provider_crud, None)
            vm.load_details()
            soft_assert(vm.on_details())

        # check table counts vs what we are expecting
        for table_name in sorted(test_data['counts'].keys()):
            expected_count = test_data['counts'][table_name]
            actual_count = db_counts[table_name]
            soft_assert(actual_count == expected_count, 'Table ' + table_name + '(' +
                str(actual_count) + ') not matching expected(' + str(expected_count) + ')')
