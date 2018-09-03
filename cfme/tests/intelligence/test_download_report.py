# -*- coding: utf-8 -*-
import pytest
import os
import shutil
from cfme.utils.wait import wait_for


def clean_temp_directory():
    """ Clean the temporary directory.

    """
    pytest.fail("fix this test - we no longer have firefox profiles availiable")
    browser = None
    for root, dirs, files in os.walk(browser.firefox_profile_tmpdir):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


@pytest.fixture
def needs_firefox(appliance):
    """ Fixture which skips the test if not run under firefox.

    I recommend putting it in the first place.
    """
    browser = appliance.browser.open_browser()
    if browser.name != "firefox":
        pytest.skip(msg="This test needs firefox to run")


@pytest.fixture(scope="module")
def report(appliance):
    return appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Virtual Machines",
        menu_name="Hardware Information for VMs"
    ).queue(wait_for_finish=True)


# TODO Prevent Firefox from popping up "Save file" in order to add 'pdf' parametrization
# Files download is unsolved, since the browser runs in a separate container
@pytest.mark.skip
@pytest.mark.parametrize("filetype", ["txt", "csv"])
def test_download_report_firefox(needs_firefox, infra_provider, report, filetype):
    """ Download the report as a file and check whether it was downloaded. """
    extension = "." + filetype
    clean_temp_directory()
    report.download(filetype)

    browser = None

    wait_for(lambda: any([file.endswith(extension) for file in os.listdir(
        browser.firefox_profile_tmpdir)]), num_sec=60.0)
    clean_temp_directory()
