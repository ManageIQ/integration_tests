# -*- coding: utf-8 -*-

""" Tests used to check the operation of log collecting.

Author: Milan Falešník <mfalesni@redhat.com>
Since: 2013-02-20
"""
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
from utils.timeutil import parsetime
from utils.virtual_machines import deploy_template


pytestmark = [test_requirements.log_depot]


class LogDepotType(object):
    def __init__(self, protocol, credentials, access_dir=None, path=None):
        self.protocol = protocol
        self._param_name = self.protocol
        self.credentials = credentials
        self.access_dir = access_dir
        self.path = path
        self.machine_ip = None
        self.hostname = access_dir if access_dir else ""

    @property
    def ftp(self):
        if self.protocol == "anon_ftp":
            ftp_user_name = "anonymous"
            ftp_password = ""
            # case anonymous connection cfme works only with hardcoded "incoming" directory
            # incoming folder used for https://bugzilla.redhat.com/show_bug.cgi?id=1307019
            upload_dir = "incoming"
            ftp_host_name = self.machine_ip + self.hostname
        else:
            ftp_user_name = self.credentials["username"]
            ftp_password = self.credentials["password"]
            # if it's not anonymous using predefined credentials
            upload_dir = "/"
            ftp_host_name = self.machine_ip + self.hostname
        return FTPClient(ftp_host_name,
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
    data = conf.cfme_data.get("log_db_operations_new", {})
    depots = []
    ids = []
    creds = conf.credentials[data['credentials']]
    for protocol, proto_data in data['protocols'].iteritems():
        if proto_data['use_for_log_collection']:
            depots.append([LogDepotType(
                protocol, creds,
                proto_data.get('sub_folder', None), proto_data.get('path_on_host', None))])
            ids.append(protocol)
    testgen.parametrize(metafunc, fixtures, depots, ids=ids, scope="function")
    return


@pytest.yield_fixture(scope="session")
def depot_machine_ip():
    """ Deploy vm for depot test

    This fixture uses for deploy vm on provider from yaml and then receive it's ip
    After test run vm deletes from provider
    """
    depot_machine_name = "test_long_log_depot_{}".format(fauxfactory.gen_alphanumeric())
    data = conf.cfme_data.get("log_db_operations_new", {})
    depot_provider_key = data["log_db_depot_template"]["provider"]
    depot_template_name = data["log_db_depot_template"]["template_name"]
    prov = get_mgmt(depot_provider_key)
    deploy_template(depot_provider_key,
                    depot_machine_name,
                    template_name=depot_template_name)
    yield prov.get_ip_address(depot_machine_name)
    prov.delete_vm(depot_machine_name)


@pytest.yield_fixture(scope="function")
def configured_depot(log_depot,  depot_machine_ip):
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


def check_ftp(ftp):
    with ftp:
        # Files must have been created after start
        zip_files = ftp.filesystem.search(re.compile(r"^.*?[.]zip$"), directories=False)
        assert zip_files, "No logs found!"
    # Check the times of the files by names
    datetimes = []
    regexp = re.compile(
        r"^.*?_(?P<y1>[0-9]{4})(?P<m1>[0-9]{2})(?P<d1>[0-9]{2})_"
        r"(?P<h1>[0-9]{2})(?P<M1>[0-9]{2})(?P<S1>[0-9]{2})"
        r"_(?P<y2>[0-9]{4})(?P<m2>[0-9]{2})(?P<d2>[0-9]{2})_"
        r"(?P<h2>[0-9]{2})(?P<M2>[0-9]{2})(?P<S2>[0-9]{2})[.]zip$"
    )
    for file in zip_files:
        data = regexp.match(file.name)
        assert data, "Wrong file matching of {}".format(file.name)
        data = {key: int(value) for key, value in data.groupdict().iteritems()}
        date_from = parsetime(
            data["y1"], data["m1"], data["d1"], data["h1"], data["M1"], data["S1"])
        date_to = parsetime(data["y2"], data["m2"], data["d2"], data["h2"], data["M2"], data["S2"])
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
                            forced_streams=["5.6", "upstream"])]
                  )
def test_collect_log_depot(log_depot,depot_configured, request):
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
    depot_configured.collect_all()
    # Check it on FTP
    check_ftp(log_depot.ftp)


@pytest.mark.meta(blockers=[BZ(1436367, forced_streams=["5.8"])])
@pytest.mark.tier(3)
def test_collect_unconfigured(soft_assert, appliance):
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