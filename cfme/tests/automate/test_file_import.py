import pytest

from cfme import test_requirements
from cfme.automate.dialog_import_export import DialogImportExport
from cfme.fixtures.automate import DatastoreImport
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.log_validator import LogValidator

pytestmark = [test_requirements.automate, pytest.mark.tier(3)]


@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1715396.zip", "BZ_1715396", None)],
    ids=["sample_domain"],
)
def test_domain_import_file(import_datastore, import_data):
    """This test case Verifies that a domain can be imported from file.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: medium
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        testSteps:
            1. Navigate to Automation > Automate > Import/Export
            2. Upload zip datastore file
            3. Select domain which like to import
        expectedResults:
            1.
            2.
            3. Import should work. Check imported or not.
    """
    assert import_datastore.exists


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1720611])
@pytest.mark.parametrize("files", ["datastore_blank.zip", "dialog_blank.yml"],
                         ids=["datastore", "dialog"])
@pytest.mark.uncollectif(lambda files: files == "dialog_blank.yml" and
                         BZ(1720611, forced_streams=['5.10']).blocks)
def test_upload_blank_file(appliance, files):
    """
    Bugzilla:
        1720611

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: negative
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Create blank zip(test.zip) and yaml(test.yml) file
            2. Navigate to Automation > Automate > Import/Export and upload test.zip file
            3. Navigate to Automation > Automate > Customization > Import/Export and upload test.yml
        expectedResults:
            1.
            2. Error message should be displayed
            3. Error message should be displayed
    """
    # Download datastore file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.datastores)
    file_path = fs.download(files)

    if files == "dialog_blank.yml":
        with LogValidator("/var/www/miq/vmdb/log/production.log",
                          failure_patterns=[".*FATAL.*"]).waiting(timeout=120):

            # Import dialog yml to appliance
            import_export = DialogImportExport(appliance)
            view = navigate_to(import_export, "DialogImportExport")
            view.upload_file.fill(file_path)
            view.upload.click()
            view.flash.assert_message('Error: the uploaded file is blank')
    else:
        # Import datastore file to appliance
        datastore = appliance.collections.automate_import_exports.instantiate(
            import_type="file", file_path=file_path
        )
        view = navigate_to(datastore.parent, "All")
        with LogValidator("/var/www/miq/vmdb/log/production.log",
                          failure_patterns=[".*FATAL.*"]).waiting(timeout=120):
            view.import_file.upload_file.fill(datastore.file_path)
            view.import_file.upload.click()
            assert view.error_flash.text == "Error: import processing failed: domain: *"
