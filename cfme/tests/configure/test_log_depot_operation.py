# -*- coding: utf-8 -*-
""" Tests used to check the operation of log collecting.

Author: Milan Falešník <mfalesni@redhat.com>
Since: 2013-02-20
"""
import re
from datetime import datetime

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils import conf
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.ftp import FTPClient
from cfme.utils.ssh import SSHClient
from cfme.utils.update import update

pytestmark = [pytest.mark.long_running, test_requirements.log_depot]


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
    if not data:
        pytest.skip('No log_db_operations information!')
    creds = conf.credentials[data['credentials']]
    for protocol, proto_data in data['protocols'].items():
        if proto_data['use_for_log_collection']:
            depots.append([LogDepotType(
                protocol, creds,
                proto_data.get('sub_folder'), proto_data.get('path_on_host'))])
            ids.append(protocol)
    if metafunc.function.__name__ in ["test_collect_multiple_servers",
                                      "test_collect_single_servers"]:
        ids = ids[:1]
        depots = depots[:1]
    elif metafunc.function.__name__ == "test_log_collection_over_ipv6":
        anon_id = ids.index("anon_ftp")
        ids = [ids[anon_id]]
        depots = [depots[anon_id]]
    testgen.parametrize(metafunc, fixtures, depots, ids=ids, scope="function")
    return


@pytest.fixture(scope="module")
def configured_external_appliance(temp_appliance_preconfig, app_creds_modscope,
                                  temp_appliance_unconfig):
    hostname = temp_appliance_preconfig.hostname
    temp_appliance_unconfig.appliance_console_cli.configure_appliance_external_join(hostname,
        app_creds_modscope['username'], app_creds_modscope['password'], 'vmdb_production',
        hostname, app_creds_modscope['sshlogin'], app_creds_modscope['sshpass'])
    temp_appliance_unconfig.evmserverd.start()
    temp_appliance_unconfig.evmserverd.wait_for_running()
    temp_appliance_unconfig.wait_for_web_ui()
    return temp_appliance_unconfig


@pytest.fixture(scope="function")
def configured_depot(log_depot, depot_machine_ip, appliance):
    """ Configure selected depot provider

    This fixture used the trick that the fixtures are cached for given function.
    So if placed behind the depot_* stuff on the test function, it can actually
    take the values from them.

    It also provides a finalizer to disable the depot after test run.
    """
    log_depot.machine_ip = depot_machine_ip
    uri = '{}{}'.format(log_depot.machine_ip, log_depot.access_dir)
    server_log_depot = appliance.server.collect_logs
    with update(server_log_depot):
        server_log_depot.depot_type = log_depot.protocol
        server_log_depot.depot_name = fauxfactory.gen_alphanumeric()
        server_log_depot.uri = uri
        server_log_depot.username = log_depot.credentials.username
        server_log_depot.password = log_depot.credentials.password
    yield server_log_depot
    server_log_depot.clear()


def check_ftp(appliance, ftp, server_name, server_zone_id, check_contents=False):
    server_string = '{}_{}'.format(server_name, server_zone_id)
    with ftp:
        # Files must have been created after start with server string in it (for ex. EVM_1)
        date_group = '(_.*?){4}'
        zip_files = ftp.filesystem.search(re.compile(
            r"^.*{}{}[.]zip$".format(server_string, date_group)), directories=False)
        assert zip_files, "No logs found!"
        # Collection of Models and Dialogs introduced in 5.10 but it work only in 5.11 (BZ 1656318)
        if appliance.version >= "5.11" and not BZ(1706989).blocks:
            models_files = ftp.filesystem.search(re.compile(
                r"^Models_.*{}[.]zip$".format(server_string)), directories=False
            )
            assert models_files, 'No models files found'
            dialogs_files = ftp.filesystem.search(re.compile(
                r"^Dialogs_.*{}[.]zip$".format(server_string)), directories=False
            )
            assert dialogs_files, 'No dialogs files found'

    # Check the times of the files by names
    datetimes = []
    for zip_file in zip_files:
        # files looks like "Current_region_0_default_1_EVM_1_20170127_043343_20170127_051010.zip"
        # 20170127_043343 - date and time
        date = zip_file.name.split("_")
        date_from = date[7] + date[8]
        # removing ".zip" from last item
        date_to = date[9] + date[10][:-4]
        try:
            date_from = datetime.strptime(date_from, "%Y%m%d%H%M%S")
            date_to = datetime.strptime(date_to, "%Y%m%d%H%M%S")
            log_files = ["log/ansible_tower", "pgsql/data/postgresql.conf"]
            if ftp.login != 'anonymous' and check_contents:  # can't login as anon using SSH
                with SSHClient(hostname=ftp.host,
                               username=ftp.login,
                               password=ftp.password) as log_ssh:
                    for log in log_files:
                        if "ansible" in log and BZ(1751961).blocks:
                            continue
                        result = log_ssh.run_command(
                            "unzip -l ~{} | grep {}".format(zip_file.path, log), ensure_user=True
                        )
                        assert log in result.output
                        log_file_size = result.output.split()[0]
                        assert int(log_file_size) > 0, "Log file is empty!"
        except ValueError:
            assert False, f"Wrong file matching in {zip_file.name} for {log}"
        datetimes.append((date_from, date_to, zip_file.name))

    # Check for the gaps
    if len(datetimes) > 1:
        for i in range(len(datetimes) - 1):
            dt = datetimes[i + 1][0] - datetimes[i][1]
            assert dt.total_seconds() >= 0.0, (
                "Negative gap between log files ({}, {})".format(
                    datetimes[i][2], datetimes[i + 1][2])
            )


@pytest.fixture
def service_request(appliance, ansible_catalog_item):
    request_descr = \
        "Provisioning Service [{name}] from [{name}]".format(name=ansible_catalog_item.name)
    service_request_ = appliance.collections.requests.instantiate(description=request_descr)
    yield service_request_

    if service_request_.exists():
        service_request_.remove_request()


@pytest.mark.tier(3)
@pytest.mark.nondestructive
@pytest.mark.meta(automates=[1652116, 1656318, 1706989])
def test_collect_log_depot(log_depot, appliance, service_request, configured_depot, request):
    """ Boilerplate test to verify functionality of this concept

    Will be extended and improved.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        initialEstimate: 1/4h
    Bugzilla:
        1652116
        1656318
        1706989
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
    check_ftp(appliance=appliance, ftp=log_depot.ftp, server_name=appliance.server.name,
              server_zone_id=appliance.server.sid, check_contents=True)


@pytest.mark.tier(3)
def test_collect_unconfigured(appliance):
    """ Test checking is collect button enable and disable after log depot was configured


    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
    """
    server_log_depot = appliance.server.collect_logs
    with update(server_log_depot):
        server_log_depot.depot_type = 'anon_ftp'
        server_log_depot.depot_name = fauxfactory.gen_alphanumeric()
        server_log_depot.uri = fauxfactory.gen_alphanumeric()

    view = navigate_to(server_log_depot, 'DiagnosticsCollectLogs')
    # check button is enable after adding log depot
    assert view.toolbar.collect.is_displayed
    server_log_depot.clear()
    # check button is disable after removing log depot
    assert not view.toolbar.collect.is_displayed
    # check it's also disabled on zone level
    view_zone = navigate_to(appliance.server.zone.collect_logs, 'DiagnosticsCollectLogs')
    assert not view_zone.toolbar.collect.is_displayed


@pytest.mark.parametrize('from_secondary', [True, False], ids=['from_secondary', 'from_current'])
@pytest.mark.parametrize('zone_collect', [True, False], ids=['zone_collect', 'server_collect'])
@pytest.mark.parametrize('collect_type', ['all', 'current'], ids=['collect_all', 'collect_current'])
@pytest.mark.tier(3)
def test_collect_multiple_servers(log_depot, temp_appliance_preconfig, depot_machine_ip, request,
                                  configured_external_appliance, zone_collect, collect_type,
                                  from_secondary):

    """
    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        initialEstimate: 1/4h
    """
    appliance = temp_appliance_preconfig
    log_depot.machine_ip = depot_machine_ip
    collect_logs = (
        appliance.server.zone.collect_logs if zone_collect else appliance.server.collect_logs)
    request.addfinalizer(collect_logs.clear)

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
        uri = '{}{}'.format(log_depot.machine_ip, log_depot.access_dir)
        with update(collect_logs):
            collect_logs.second_server_collect = from_secondary
            collect_logs.depot_type = log_depot.protocol
            collect_logs.depot_name = fauxfactory.gen_alphanumeric()
            collect_logs.uri = uri
            collect_logs.username = log_depot.credentials.username
            collect_logs.password = log_depot.credentials.password

        if collect_type == 'all':
            collect_logs.collect_all()
        else:
            collect_logs.collect_current()

    secondary_servers = appliance.server.secondary_servers
    secondary_server = secondary_servers[0] if secondary_servers else None

    if from_secondary and zone_collect:
        check_ftp(appliance, log_depot.ftp, secondary_server.name, secondary_server.sid)
        check_ftp(appliance, log_depot.ftp, appliance.server.name, appliance.server.zone.id)
    elif from_secondary:
        check_ftp(appliance, log_depot.ftp, secondary_server.name, secondary_server.sid)
    else:
        check_ftp(appliance, log_depot.ftp, appliance.server.name, appliance.server.zone.id)


@pytest.mark.parametrize('zone_collect', [True, False], ids=['zone_collect', 'server_collect'])
@pytest.mark.parametrize('collect_type', ['all', 'current'], ids=['collect_all', 'collect_current'])
@pytest.mark.tier(3)
def test_collect_single_servers(log_depot, appliance, depot_machine_ip, request, zone_collect,
                                collect_type):
    """
    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        initialEstimate: 1/4h
    """
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

    uri = '{}{}'.format(log_depot.machine_ip, log_depot.access_dir)
    collect_logs = (
        appliance.server.zone.collect_logs if zone_collect else appliance.server.collect_logs)
    with update(collect_logs):
        collect_logs.depot_type = log_depot.protocol
        collect_logs.depot_name = fauxfactory.gen_alphanumeric()
        collect_logs.uri = uri
        collect_logs.username = log_depot.credentials.username
        collect_logs.password = log_depot.credentials.password
    request.addfinalizer(collect_logs.clear)
    if collect_type == 'all':
        collect_logs.collect_all()
    else:
        collect_logs.collect_current()

    check_ftp(appliance, log_depot.ftp, appliance.server.name, appliance.server.sid)


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1452224])
def test_log_collection_over_ipv6(log_depot, depot_machine_ipv4_and_ipv6, appliance, request):
    """
    Bug 1452224 - Log Collection fails via IPv6

    Bugzilla:
        1452224

    An IPv6 FTP server can be validated for log collection, and log
    collection succeeds.

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    ipv4, ipv6 = depot_machine_ipv4_and_ipv6
    # FTPClient gives error with ipv6
    log_depot.machine_ip = ipv4

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

    uri = f"{ipv6}{log_depot.access_dir}"
    collect_logs = appliance.server.collect_logs
    with update(collect_logs):
        collect_logs.depot_type = log_depot.protocol
        collect_logs.depot_name = fauxfactory.gen_alphanumeric()
        collect_logs.uri = uri
        collect_logs.username = log_depot.credentials.username
        collect_logs.password = log_depot.credentials.password
    request.addfinalizer(collect_logs.clear)
    collect_logs.collect_all()

    check_ftp(appliance, log_depot.ftp, appliance.server.name, appliance.server.sid)
