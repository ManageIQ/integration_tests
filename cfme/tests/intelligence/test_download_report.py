# -*- coding: utf-8 -*-
import pytest
import os
import shutil
from cfme.intelligence.reports.reports import CannedSavedReport
from cfme.utils.wait import wait_for
from cfme.utils import browser


def clean_temp_directory():
    """ Clean the temporary directory.

    """
    for root, dirs, files in os.walk(browser.firefox_profile_tmpdir):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


@pytest.fixture
def needs_firefox():
    """ Fixture which skips the test if not run under firefox.

    I recommend putting it in the first place.
    """
    browser.ensure_browser_open()
    if browser.browser().name != "firefox":
        pytest.skip(msg="This test needs firefox to run")


@pytest.fixture(scope="module")
def report():
    path = ["Configuration Management", "Virtual Machines", "Hardware Information for VMs"]
    return CannedSavedReport(path, CannedSavedReport.queue_canned_report(path))


# TODO Prevent Firefox from popping up "Save file" in order to add 'pdf' parametrization
# Files download is unsolved, since the browser runs in a separate container
@pytest.mark.skip
@pytest.mark.parametrize("filetype", ["txt", "csv"])
def test_download_report_firefox(needs_firefox, infra_provider, report, filetype):
    """ Download the report as a file and check whether it was downloaded. """
    extension = "." + filetype
    clean_temp_directory()
    report.download(filetype)
    wait_for(lambda: any([file.endswith(extension) for file in os.listdir(
        browser.firefox_profile_tmpdir)]), num_sec=60.0)
    clean_temp_directory()
