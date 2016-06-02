# -*- coding: utf-8 -*-

""" Tests used to check the operation of log collecting.

Author: Milan Falešník <mfalesni@redhat.com>
Since: 2013-02-20
"""
import fauxfactory
import pytest
import re
from utils.timeutil import parsetime
from utils import conf, testgen
from utils.ftp import FTPClient
from utils.path import log_path
from cfme.configure import configuration as configure
from cfme.web_ui import toolbar


def pytest_generate_tests(metafunc):
    """ Parametrizes the logdepot tests according to cfme_data YAML file.

    YAML structure (shared with db backup tests) is as follows:

    log_db_depot:
        machine1:
            credentials: machine1_creds
            smb:
                hostname: smb.example.com/sharename
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
        machine2:
            credentials: machine2_creds
            smb:
                hostname: smb.example2.com/sharename
                path_on_host: /path/on/host
                use_for_log_collection: True
                use_for_db_backups: False
            nfs:
                hostname: nfs.example2.com/path/on/host
                use_for_log_collection: False
                use_for_db_backups: True
            ftp:
                hostname: ftp.example2.com
                use_for_log_collection: True

    Each Machine ID must have ftp configured to check uploaded files.
    If ftp is not present for the machine, it will fail with an Exception.
    The folders exposed over these three protocols should point into the same folder,
    because checking is done by FTP.

    This generator provides these fixtures:

    - depot_type: ftp, smb or nfs.
    - depot_machine: hostname or IP of the depot machine from YAML.
    - depot_credentials
    - depot_ftp: FTP client targeted for the machine.

    The first three are used for ``depot_configured`` fixture.
    Because of this, these fixtures must preceed the ``depot_configured`` fixture
    to ensure that they are filled before ``depot_configured`` gets called.

    @todo: Think about using SSH for file check? Or FTP is enough?
    """
    data = conf.cfme_data.get("log_db_depot", {})

    # Fixtures used for parametrisation
    fixtures = [
        "depot_type",
        "depot_machine",
        "depot_credentials",
        "depot_ftp"
    ]

    # Permitted methods
    methods = [
        "ftp",
        "smb",
        "nfs",
        "anon_ftp"
    ]

    # FTP credentials for machines
    # Used for checking the uploaded content
    machines_ftp = {}

    try:
        for fixture_name in fixtures:
            assert fixture_name in metafunc.fixturenames
    except AssertionError:
        return

    parametrized = []
    for machine_id, machine_content in data.iteritems():
        credentials = machine_content.get("credentials", None)
        if credentials:
            try:
                credentials = conf.credentials[credentials]
            except KeyError:
                raise Exception(
                    "No credentials with id {} found in credentials file!".format(credentials))
        else:
            raise Exception("No credentials found in cfme_data for machine {}!".format(machine_id))
        for depot_type, depot_type_content in machine_content.iteritems():
            if depot_type == 'credentials':
                continue
            assert depot_type in methods, "{} is illegal depot type".format(depot_type)
            assert "hostname" in depot_type_content,\
                "cfme_data.yaml/log_db_depot/{}/{} does not contain hostname!"\
                .format(machine_id, depot_type)

            hostname = depot_type_content["hostname"]
            if depot_type == "ftp" and machine_id not in machines_ftp:
                machines_ftp[machine_id] = credentials
                machines_ftp[machine_id]["hostname"] = hostname

            assert "use_for_log_collection" in depot_type_content,\
                "cfme_data.yaml/log_db_depot/{}/{} does not contain use_for_log_collection key!"\
                .format(machine_id, depot_type)
            use_for_log_collection = depot_type_content["use_for_log_collection"]
            if not use_for_log_collection:
                continue
            parametrized.append((depot_type, hostname, credentials, machine_id))
    new_parametrized = []
    # We have to inject also the ftp connection into the fixtures
    for depot_type, hostname, credentials, machine_id in parametrized:
        if depot_type != "anon_ftp":
            assert machine_id in machines_ftp, "Machine {} does not have FTP access"\
                .format(machine_id)
            ftp_credentials = machines_ftp[machine_id]

        def get_ftp(depot_type=depot_type):
            """ Returns FTP client generator targeted to the depot machine.

            Usage:

            with depot_ftp() as ftp:
                ftp.recursively_delete()    # And so on ...

            """
            # Condition to check if it anonymous ftp or not, use default anonymous user
            if depot_type == "anon_ftp":
                ftp_user_name = "anonymous"
                ftp_password = ""
                # case anonymous connection cfme works only with hardcoded "incoming" directory
                # incoming folder used for https://bugzilla.redhat.com/show_bug.cgi?id=1307019
                upload_dir = "incoming"
                ftp_host_name = hostname
            else:
                ftp_user_name = ftp_credentials["username"]
                ftp_password = ftp_credentials["password"]
                # if it's not anonymous using predefined credentials
                upload_dir = "/"
                ftp_host_name = ftp_credentials["hostname"]
            return FTPClient(ftp_host_name,
                             ftp_user_name,
                             ftp_password,
                             upload_dir)
        param_tuple = (depot_type, hostname, credentials, get_ftp)
        if param_tuple not in new_parametrized:
            new_parametrized.append(param_tuple)
    testgen.parametrize(metafunc, fixtures, new_parametrized, scope="function")


@pytest.fixture(scope="function")
def depot_configured(request, depot_type, depot_machine, depot_credentials):
    """ Configure selected depot provider

    This fixture used the trick that the fixtures are cached for given function.
    So if placed behind the depot_* stuff on the test function, it can actually
    take the values from them.

    It also provides a finalizer to disable the depot after test run.
    """
    if depot_type not in ["nfs", "anon_ftp"]:
        credentials = configure.ServerLogDepot.Credentials(
            depot_type,
            fauxfactory.gen_alphanumeric(),
            depot_machine,
            username=depot_credentials["username"],
            password=depot_credentials["password"],
        )
    else:
        credentials = configure.ServerLogDepot.Credentials(
            depot_type,
            fauxfactory.gen_alphanumeric(),
            depot_machine,
        )
    # Fails on upstream - BZ1108087
    credentials.update()
    request.addfinalizer(configure.ServerLogDepot.Credentials.clear)
    return credentials


@pytest.mark.nondestructive
@pytest.mark.meta(blockers=[1335824], forced_streams=['5.6', 'upstream'])
def test_collect_log_depot(depot_type, depot_machine, depot_credentials, depot_ftp,
                           depot_configured, soft_assert, request):
    """ Boilerplate test to verify functionality of this concept

    Will be extended and improved.
    """
    # Wipe the FTP contents in the end
    @request.addfinalizer
    def _clear_ftp():
        with depot_ftp() as ftp:
            ftp.cwd(ftp.upload_dir)
            ftp.recursively_delete()

    # Prepare empty workspace
    with depot_ftp() as ftp:
        # move to upload folder
        ftp.cwd(ftp.upload_dir)
        # delete all files
        ftp.recursively_delete()

    # Start the collection
    configure.ServerLogDepot.collect_all()
    # Check it on FTP
    with depot_ftp() as ftp:
        # Files must have been created after start
        zip_files = ftp.filesystem.search(re.compile(r"^.*?[.]zip$"), directories=False)
        assert zip_files, "No logs found!"

        # And must be older than the start time.
        for file in zip_files:
            soft_assert(file.local_time < parsetime.now(), "{} is older.".format(file.name))

        # No file contains 'unknown_unknown' sequence
        # BZ: 1018578
        bad_files = ftp.filesystem.search(re.compile(r"^.*?unknown_unknown.*?[.]zip$"),
                                          directories=False)
        if bad_files:
            print_list = []
            for file in bad_files:
                random_name = "{}.zip".format(fauxfactory.gen_alphanumeric())
                download_file_name = log_path.join(random_name).strpath
                file.download(download_file_name)
                print_list.append((file, random_name))

            pytest.fail(
                "BUG1018578: Files {} present!".format(
                    ", ".join("{} as {}".format(f, r) for f, r in print_list)))

    # Check the times of the files by names
    datetimes = []
    regexp = re.compile(
        r"^.*?_(?P<y1>[0-9]{4})(?P<m1>[0-9]{2})(?P<d1>[0-9]{2})_"
        r"(?P<h1>[0-9]{2})(?P<M1>[0-9]{2})(?P<S1>[0-9]{2})"
        r"_(?P<y2>[0-9]{4})(?P<m2>[0-9]{2})(?P<d2>[0-9]{2})_"
        r"(?P<h2>[0-9]{2})(?P<M2>[0-9]{2})(?P<S2>[0-9]{2})[.]zip$"
    )
    failed = False
    for file in zip_files:
        data = regexp.match(file.name)
        if not soft_assert(data, "Wrong file matching of {}".format(file.name)):
            failed = True
            continue
        data = {key: int(value) for key, value in data.groupdict().iteritems()}
        date_from = parsetime(
            data["y1"], data["m1"], data["d1"], data["h1"], data["M1"], data["S1"])
        date_to = parsetime(data["y2"], data["m2"], data["d2"], data["h2"], data["M2"], data["S2"])
        datetimes.append((date_from, date_to, file.name))

    if not failed:
        # Check for the gaps
        if len(datetimes) > 1:
            for i in range(len(datetimes) - 1):
                dt = datetimes[i + 1][0] - datetimes[i][1]
                soft_assert(
                    dt.total_seconds() >= 0.0,
                    "Negative gap between log files ({}, {})".format(
                        datetimes[i][2], datetimes[i + 1][2]))


def test_collect_unconfigured(request, soft_assert):
    """ Test checking is collect button enable and disable after log depot was configured

    """
    request.addfinalizer(configure.ServerLogDepot.Credentials.clear)
    log_credentials = configure.ServerLogDepot.Credentials("smb",
                                                           "testname",
                                                           "testhost",
                                                           username="testusername",
                                                           password="testpassword")
    log_credentials.update(validate=False)
    # check button is enable after adding log depot
    soft_assert(toolbar.is_greyed("Collect", "Collect all logs") is False)
    configure.ServerLogDepot.Credentials.clear()
    # check button is disable after removing log depot
    soft_assert(toolbar.is_greyed("Collect", "Collect all logs") is True)
