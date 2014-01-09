# -*- coding: utf-8 -*-
""" Tests used to check the operation of log collecting.

@author: Milan Falešník <mfalesni@redhat.com>
@since: 2013-11-15
"""

import pytest
import re
from datetime import datetime
from functools import partial
from utils import conf
from utils.ftp import FTPClient
from time import strftime, gmtime, sleep


def get_current_time_GMT():
    """ Because FTP loves GMT.

    Does not return seconds as FTP also does not expose seconds.
    This would make trouble when comparing the times.
    """
    return datetime.strptime(strftime("%Y-%m-%d %H:%M", gmtime()), "%Y-%m-%d %H:%M")


@pytest.fixture
def pg_diagnostics(cnf_configuration_pg):
    """ Page Configure / Configuration / Diagnostics

    """
    return cnf_configuration_pg.click_on_diagnostics()


@pytest.fixture
def pg_this_server_diagnostics(pg_diagnostics):
    """ Page Configure / Configuration / Diagnostics / Current server

    """
    return pg_diagnostics.click_on_current_server_tree_node()


@pytest.fixture
def pg_collect_logs(pg_this_server_diagnostics):
    """ Page Configure / Configuration / Diagnostics / Current server / Collect Logs

    """
    return pg_this_server_diagnostics.click_on_collect_logs_tab()


def pytest_generate_tests(metafunc):
    """ Parametrizes the logdepot tests according to cfme_data YAML file.

    YAML structure is as follows:

    log_depot:
        ftp:            # Protocol
            machine1:   # Machine ID
                credentials: cred_for_machine1_ftp
                hostname: somehost
            machine2:
                credentials: cred_for_machine2_ftp
                hostname: some_other_host
        smb:
            machine1:
                credentials: cred_for_machine1_smb
                hostname: somehost/someshare
            machine2:
                credentials: cred_for_machine2_smb
                hostname: some_other_host/other_share
        nfs:
            machine2:
                hostname: somehost:/some/folder

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
    data = conf.cfme_data.get("log_depot", {})

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
        "nfs"
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
    for depot_type, depot_type_content in data.iteritems():
        assert depot_type in methods, "%s is illegal depot type" % depot_type
        for machine_id, machine_content in depot_type_content.iteritems():
            assert "hostname" in machine_content,\
                "cfme_data.yaml/log_depot/%s/%s does not contain hostname!" %\
                (depot_type, machine_id)

            hostname = machine_content["hostname"]
            credentials = machine_content.get("credentials", None)
            if depot_type != "nfs" and not credentials:
                raise Exception("Only NFS can have no credentials!")
            if credentials:
                try:
                    credentials = conf.credentials[credentials]
                except KeyError:
                    raise Exception("No credentials present for machine %s" % machine_id)
            if depot_type == "ftp" and machine_id not in machines_ftp:
                machines_ftp[machine_id] = credentials
                machines_ftp[machine_id]["hostname"] = hostname
            parametrized.append((depot_type, hostname, credentials, machine_id))
    new_parametrized = []
    # We have to inject also the ftp connection into the fixtures
    for depot_type, hostname, credentials, machine_id in parametrized:
        assert machine_id in machines_ftp, "Machine %s does not have FTP access" % machine_id
        ftp_credentials = machines_ftp[machine_id]

        def get_ftp():
            """ Returns FTP client generator targeted to the depot machine.

            Usage:

            with depot_ftp() as ftp:
                ftp.recursively_delete()    # And so on ...

            """
            return FTPClient(ftp_credentials["hostname"],
                             ftp_credentials["username"],
                             ftp_credentials["password"])
        param_tuple = (depot_type, hostname, credentials, get_ftp)
        if param_tuple not in new_parametrized:
            new_parametrized.append(param_tuple)
    metafunc.parametrize(fixtures, new_parametrized, scope="function")


@pytest.fixture(scope="function")
def depot_configured(request, depot_type, depot_machine, depot_credentials, pg_collect_logs):
    """ Configure selected depot provider

    This fixture used the trick that the fixtures are cached for given function.
    So if placed behind the depot_* stuff on the test function, it can actually
    take the values from them.

    It also provides a finalizer to disable the depot after test run.
    """
    edit_pg = pg_collect_logs.edit()
    if depot_type not in ["nfs"]:
        assert edit_pg.fill_credentials(depot_type,
                                        depot_machine,
                                        user=depot_credentials["username"],
                                        password=depot_credentials["password"])
    else:
        assert edit_pg.fill_credentials(depot_type,
                                        depot_machine)
    collect = edit_pg.save_settings()
    assert "Log Depot Settings were saved" in collect.flash.message

    request.addfinalizer(partial(unconfigure, pg_collect_logs))


def unconfigure(pg_collect_logs):
    edit_pg = pg_collect_logs.edit()
    if edit_pg.depot_type is not None:
        edit_pg.depot_type = None
        edit_pg.save_settings()


def test_unconfigure_depot(pg_collect_logs):
    unconfigure(pg_collect_logs)


@pytest.mark.nondestructive
def test_collect_log_depot(depot_type,
                           depot_machine,
                           depot_credentials,
                           depot_ftp,
                           depot_configured,
                           pg_collect_logs):
    """ Boilerplate test to verify functionality of this concept

    Will be extended and improved.
    """
    # Prepare empty workspace
    with depot_ftp() as ftp:
        ftp.recursively_delete()

    # Start the collection
    started = get_current_time_GMT()
    pg_collect_logs.collect_all_logs()
    sleep(45)   # To make the eventual already written text disappear
                # This is because previous last message is left and if the message was
                # 'were successfully collected', then it would be a false success.
    pg_collect_logs.refresh()
    pg_collect_logs.wait_last_message(lambda text: "were successfully collected" in text)

    # Check it on FTP
    with depot_ftp() as ftp:
        # Files must have been created after start
        zip_files = ftp.filesystem.search(re.compile(r"^.*?[.]zip$"), directories=False)
        assert zip_files, "No logs found!"

        # And must be older than the start time.
        for file in zip_files:
            assert file.time >= started, "%s is older." % file.name

        # No file contains 'unknown_unknown' sequence
        # BZ: 1018578
        bad_files = ftp.filesystem.search(re.compile(r"^.*?unknown_unknown.*?[.]zip$"),
                                          directories=False)
        if bad_files:
            raise Exception("BUG1018578: Files %s present!" % ", ".join(bad_files))

        # And clean it up
        ftp.recursively_delete()

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
        assert data, "Wrong file matching"
        data = {key: int(value) for key, value in data.groupdict().iteritems()}
        date_from = datetime(data["y1"], data["m1"], data["d1"], data["h1"], data["M1"], data["S1"])
        date_to = datetime(data["y2"], data["m2"], data["d2"], data["h2"], data["M2"], data["S2"])
        datetimes.append((date_from, date_to))

    # Check for the gaps
    if len(datetimes) > 1:
        for i in range(len(datetimes) - 1):
            dt = datetimes[i + 1][0] - datetimes[i][1]
            assert dt.total_seconds() >= 0.0, "Negative gap between log files"
