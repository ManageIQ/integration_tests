# -*- coding: utf-8 -*-
import pytest
import random
import os
import shutil
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


@pytest.fixture
def needs_firefox():
    """ Fixture which skips the test if not run under firefox.

    I recommend putting it in the first place.
    """
    if browser.browser().name != "firefox":
        pytest.skip(msg="This test needs firefox to run")


def test_have_some_reports(intel_reports_pg):
    """ Ensure we have something to test on.

    Open the Saved Reports accordion. If there are no saved reports, then it goies to the Reports
    accordion and queues one of them. Then it waits until it's finished.
    """
    saved = intel_reports_pg.click_on_saved_reports()
    if not saved.has_any_finished_report:
        reports = saved.click_on_reports()
        rtype = reports.select_report_type("Hardware Information for VMs")
        lst = rtype.queue_report()
        lst.wait_all_reports_finished()


@pytest.mark.requires_test("test_have_some_reports")
@pytest.mark.parametrize("filetype", ["txt", "csv", "pdf"])
@pytest.sel.go_to('dashboard')
def test_download_report_firefox(needs_firefox, intel_reports_pg, filetype):
    """ Download the report as a file and check whether it was downloaded.

    This test skips for PDF as there are some issues with it.
    """
    if filetype == "pdf":
        pytest.skip(msg="There were some troubles with FF downloading PDF so this test is disabled")
    method = "download_%s" % filetype
    extension = "." + filetype
    saved = intel_reports_pg.click_on_saved_reports()
    report = random.choice(saved.all_saved_reports)
    report = saved.click_through_report(report["name"])
    clean_temp_directory()
    getattr(report, method)()   # report.download_<filetype>()
    wait_for(
        lambda: any(
            [file.endswith(extension)
             for file
             in os.listdir(browser.firefox_profile_tmpdir)]
        ),
        num_sec=TIMEOUT
    )
    clean_temp_directory()
