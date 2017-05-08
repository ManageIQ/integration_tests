# -*- coding: utf-8 -*-

""" Tests used to check the operation of log collecting.

Author: Milan Falešník <mfalesni@redhat.com>
Since: 2013-02-20
"""
from datetime import datetime
import fauxfactory
import pytest
import re

from cfme import test_requirements
from cfme.configure import configuration as configure
from utils import conf, testgen
from utils.appliance.implementations.ui import navigate_to
from utils.blockers import BZ
from utils.ftp import FTPClient
from utils.providers import get_mgmt
from utils.version import current_version
from utils.virtual_machines import deploy_template


pytestmark = [test_requirements.log_depot]


class LogDepotType(object):
    def __init__(self, protocol, credentials, access_dir=None, path=None):
        self.protocol = protocol
        self._param_name = self.protocol
        self.credentials = credentials
        self.access_dir = access_dir or ""
        self.path = path
        self.machine_ip = None

    @property
    def ftp(self):
        if self.protocol == "anon_ftp":
            ftp_user_name = "anonymous"
            ftp_password = ""
            # case anonymous connection cfme works only with hardcoded "incoming" directory
            # incoming folder used for https://bugzilla.redhat.com/show_bug.cgi?id=1307019
            upload_dir = "incoming"
        else:
            ftp_user_name = self.credentials["username"]
            ftp_password = self.credentials["password"]
            # if it's not anonymous using predefined credentials
            upload_dir = "/"
        return FTPClient(self.machine_ip,
                         ftp_user_name,
                         ftp_password,
                         upload_dir)


def pytest_generate_tests(metafunc):
    """ Parametrizes the logdepot tests according to cfme_data YAML file.

    YAML structure (shared with db backup tests) is as follows:

    log_db_depot:
        credentials: credentials_key
        protocols:
            smb:
                path_on_host: /path/on/host
                use_for_log_collection: True
                use_for_db_backups: False
            nfs:
                hostname: nfs.example.com/path/on/host
                use_for_log_collection: False
                use_for_db_backups: True
            ftp:
                hostname: ftp.example.com
                use_for_log_collection: True
    """
    if metafunc.function.__name__ == 'test_collect_unconfigured':
        return

    fixtures = ['log_depot']
    data = conf.cfme_data.get("log_db_operations", {})
    depots = []
    ids = []
    creds = conf.credentials[data['credentials']]
    for protocol, proto_data in data['protocols'].iteritems():
        if proto_data['use_for_log_collection']:
            depots.append([LogDepotType(
                protocol, creds,
                proto_data.get('sub_folder', None), proto_data.get('path_on_host', None))])
            ids.append(protocol)
    if metafunc.function.__name__ in ['test_collect_multiple_servers',
                                      "test_collect_single_servers"]:
        ids = ids[:1]
        depots = depots[:1]
    testgen.parametrize(metafunc, fixtures, depots, ids=ids, scope="function")
    return


@pytest.yield_fixture(scope="module")
def depot_machine_ip():
    """ Deploy vm for depot test

    This fixture uses for deploy vm on provider from yaml and then receive it's ip
    After test run vm deletes from provider
    """
    depot_machine_name = "test_long_log_depot_{}".format(fauxfactory.gen_alphanumeric())
    data = conf.cfme_data.get("log_db_operations", {})
    depot_provider_key = data["log_db_depot_template"]["provider"]
    depot_template_name = data["log_db_depot_template"]["template_name"]
    prov = get_mgmt(depot_provider_key)
    deploy_template(depot_provider_key,
                    depot_machine_name,
                    template_name=depot_template_name)
    yield prov.get_ip_address(depot_machine_name)
    prov.delete_vm(depot_machine_name)


@pytest.fixture(scope="module")
def configured_external_appliance(temp_appliance_preconfig, app_creds_modscope,
                                  temp_appliance_unconfig):
    hostname = temp_appliance_preconfig.address
    temp_appliance_unconfig.appliance_console_cli.configure_appliance_external_join(hostname,
        app_creds_modscope['username'], app_creds_modscope['password'], 'vmdb_production',
        hostname, app_creds_modscope['sshlogin'], app_creds_modscope['sshpass'])
    temp_appliance_unconfig.start_evm_service()
    temp_appliance_unconfig.wait_for_evm_service()
    temp_appliance_unconfig.wait_for_web_ui()
    return temp_appliance_unconfig


@pytest.yield_fixture(scope="function")
def configured_depot(log_depot, depot_machine_ip):
    """ Configure selected depot provider

    This fixture used the trick that the fixtures are cached for given function.
    So if placed behind the depot_* stuff on the test function, it can actually
    take the values from them.

    It also provides a finalizer to disable the depot after test run.
    """
    log_depot.machine_ip = depot_machine_ip
    uri = log_depot.machine_ip + log_depot.access_dir
    log_depot = configure.ServerLogDepot(log_depot.protocol,
                                         depot_name=fauxfactory.gen_alphanumeric(),
                                         uri=uri,
                                         username=log_depot.credentials["username"],
                                         password=log_depot.credentials["password"]
                                         )
    log_depot.create()
    yield log_depot
    log_depot.clear()


def check_ftp(ftp, server_name, server_zone_id):
    server_string = server_name + "_" + str(server_zone_id)
    with ftp:
        # Files must have been created after start with server string in it (for ex. EVM_1)
        zip_files = ftp.filesystem.search(re.compile(r"^.*{}.*?[.]zip$".format(server_string)),
                                          directories=False)
        assert zip_files, "No logs found!"
    # Check the times of the files by names
    datetimes = []
    for file in zip_files:
        # files looks like "Current_region_0_default_1_EVM_1_20170127_043343_20170127_051010.zip"
        # 20170127_043343 - date and time
        date = file.name.split("_")
        date_from = date[7] + date[8]
        # removing ".zip" from last item
        date_to = date[9] + date[10][:-4]
        try:
            date_from = datetime.strptime(date_from, "%Y%m%d%H%M%S")
            date_to = datetime.strptime(date_to, "%Y%m%d%H%M%S")
        except ValueError:
            assert False, "Wrong file matching of {}".format(file.name)
        datetimes.append((date_from, date_to, file.name))

    # Check for the gaps
    if len(datetimes) > 1:
        for i in range(len(datetimes) - 1):
            dt = datetimes[i + 1][0] - datetimes[i][1]
            assert dt.total_seconds() >= 0.0, \
                "Negative gap between log files ({}, {})".format(
                    datetimes[i][2], datetimes[i + 1][2])


@pytest.mark.tier(3)
@pytest.mark.nondestructive
@pytest.mark.meta(blockers=[BZ(1341502, unblock=lambda log_depot: log_depot.protocol != "anon_ftp",
                            forced_streams=["5.6", "5.7", "5.8", "upstream"])]
                  )
def test_collect_log_depot(log_depot, appliance, configured_depot, request):
    """ Boilerplate test to verify functionality of this concept

    Will be extended and improved.
    """
    # Wipe the FTP contents in the end
    @request.addfinalizer
    def _clear_ftp():
        with log_depot.ftp as ftp:
            ftp.cwd(ftp.upload_dir)
            ftp.recursively_delete()

    # Prepare empty workspace
    with log_depot.ftp as ftp:
        # move to upload folder
        ftp.cwd(ftp.upload_dir)
        # delete all files
        ftp.recursively_delete()

    # Start the collection
    configured_depot.collect_all()
    # Check it on FTP
    check_ftp(log_depot.ftp, appliance.server_name(), appliance.server_zone_id())


@pytest.mark.meta(blockers=[BZ(1436367, forced_streams=["5.8"])])
@pytest.mark.tier(3)
def test_collect_unconfigured(appliance):
    """ Test checking is collect button enable and disable after log depot was configured

    """
    log_credentials = configure.ServerLogDepot("anon_ftp",
                                               depot_name=fauxfactory.gen_alphanumeric(),
                                               uri=fauxfactory.gen_alphanumeric())

    log_credentials.create()
    view = navigate_to(appliance.server, 'DiagnosticsCollectLogs')
    # check button is enable after adding log depot
    assert view.collect.item_enabled('Collect all logs') is True
    log_credentials.clear()
    # check button is disable after removing log depot
    assert view.collect.item_enabled('Collect all logs') is False


@pytest.mark.uncollectif(lambda from_slave: from_slave and
                         BZ.bugzilla.get_bug(1443927).is_opened and current_version() >= '5.8')
@pytest.mark.meta(blockers=[BZ(1436367, forced_streams=["5.8"])])
@pytest.mark.parametrize('from_slave', [True, False], ids=['from_slave', 'from_master'])
@pytest.mark.parametrize('zone_collect', [True, False], ids=['zone_collect', 'server_collect'])
@pytest.mark.parametrize('collect_type', ['all', 'current'], ids=['collect_all', 'collect_current'])
@pytest.mark.tier(3)
def test_collect_multiple_servers(log_depot, temp_appliance_preconfig, depot_machine_ip, request,
                                  configured_external_appliance, zone_collect, collect_type,
                                  from_slave):

    appliance = temp_appliance_preconfig
    log_depot.machine_ip = depot_machine_ip

    @request.addfinalizer
    def _clear_ftp():
        with log_depot.ftp as ftp:
            ftp.cwd(ftp.upload_dir)
            ftp.recursively_delete()

    # Prepare empty workspace
    with log_depot.ftp as ftp:
        # move to upload folder
        ftp.cwd(ftp.upload_dir)
        # delete all files
        ftp.recursively_delete()

    with appliance:
        uri = log_depot.machine_ip + log_depot.access_dir
        depot = configure.ServerLogDepot(log_depot.protocol,
                                         depot_name=fauxfactory.gen_alphanumeric(),
                                         uri=uri,
                                         username=log_depot.credentials["username"],
                                         password=log_depot.credentials["password"],
                                         second_server_collect=from_slave,
                                         zone_collect=zone_collect
                                         )
        depot.create()

        if collect_type == 'all':
            depot.collect_all()
        else:
            depot.collect_current()

    if from_slave and zone_collect:
        check_ftp(log_depot.ftp, appliance.slave_server_name(), appliance.slave_server_zone_id())
        check_ftp(log_depot.ftp, appliance.server_name(), appliance.server_zone_id())
    elif from_slave:
        check_ftp(log_depot.ftp, appliance.slave_server_name(), appliance.slave_server_zone_id())
    else:
        check_ftp(log_depot.ftp, appliance.server_name(), appliance.server_zone_id())


@pytest.mark.meta(blockers=[BZ(1436367, forced_streams=["5.8"])])
@pytest.mark.parametrize('zone_collect', [True, False], ids=['zone_collect', 'server_collect'])
@pytest.mark.parametrize('collect_type', ['all', 'current'], ids=['collect_all', 'collect_current'])
@pytest.mark.tier(3)
def test_collect_single_servers(log_depot, appliance, depot_machine_ip, request, zone_collect,
                                collect_type):
    log_depot.machine_ip = depot_machine_ip

    @request.addfinalizer
    def _clear_ftp():
        with log_depot.ftp as ftp:
            ftp.cwd(ftp.upload_dir)
            ftp.recursively_delete()

    # Prepare empty workspace
    with log_depot.ftp as ftp:
        # move to upload folder
        ftp.cwd(ftp.upload_dir)
        # delete all files
        ftp.recursively_delete()

    uri = log_depot.machine_ip + log_depot.access_dir
    depot = configure.ServerLogDepot(log_depot.protocol,
                                     depot_name=fauxfactory.gen_alphanumeric(),
                                     uri=uri,
                                     username=log_depot.credentials["username"],
                                     password=log_depot.credentials["password"],
                                     zone_collect=zone_collect
                                     )

    depot.create()
    if collect_type == 'all':
        depot.collect_all()
    else:
        depot.collect_current()

    check_ftp(log_depot.ftp, appliance.server_name(), appliance.server_zone_id())
