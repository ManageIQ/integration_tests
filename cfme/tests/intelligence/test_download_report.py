# -*- coding: utf-8 -*-
import pytest
import os
import shutil
from cfme.intelligence.reports import reports
from utils.providers import setup_a_provider as _setup_a_provider
from utils.wait import wait_for
from utils import browser


TIMEOUT = 60.0                  # Wait time for download


def clean_temp_directory():
    """ Clean the temporary directory.

    """
    for root, dirs, files in os.walk(browser.firefox_profile_tmpdir):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider("infra")


@pytest.fixture
def needs_firefox():
    """ Fixture which skips the test if not run under firefox.

    I recommend putting it in the first place.
    """
    if browser.browser().name != "firefox":
        pytest.skip(msg="This test needs firefox to run")


@pytest.fixture(scope="module")
def report():
    path = ["Configuration Management", "Virtual Machines", "Hardware Information for VMs"]
    return reports.CannedSavedReport(path, reports.queue_canned_report(*path))


@pytest.skip  # To be removed when we have solved the Docker issue
@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.sel.go_to('dashboard')
def test_download_report_firefox(needs_firefox, setup_a_provider, report, filetype):
    """ Download the report as a file and check whether it was downloaded.

    This test skips for PDF as there are some issues with it.
    BZ#1021646
    """
    extension = "." + filetype
    clean_temp_directory()
    report.download(filetype)
    wait_for(
        lambda: any(
            [file.endswith(extension)
             for file
             in os.listdir(browser.firefox_profile_tmpdir)]
        ),
        num_sec=TIMEOUT
    )
    clean_temp_directory()
