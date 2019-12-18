import os

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.dialog_import_export import DialogImportExport
from cfme.fixtures.automate import DatastoreImport
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update

pytestmark = [test_requirements.automate, pytest.mark.tier(3)]


@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1715396.zip", "bz_1715396", None)],
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
@pytest.mark.parametrize("upload_file",
                         ["datastore_blank.zip", "dialog_blank.yml"],
                         ids=["datastore", "dialog"])
@pytest.mark.uncollectif(lambda upload_file:
                         upload_file == "dialog_blank.yml" and BZ(1720611,
                                                                  forced_streams=['5.10']).blocks,
                         reason='Blank dialog import blocked by BZ 1720611')
def test_upload_blank_file(appliance, upload_file):
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
    file_path = fs.download(upload_file)

    if upload_file == "dialog_blank.yml":
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
        view = navigate_to(appliance.collections.automate_import_exports, "All")
        with LogValidator("/var/www/miq/vmdb/log/production.log",
                          failure_patterns=[".*FATAL.*"]).waiting(timeout=120):
            view.import_file.upload_file.fill(datastore.file_path)
            view.import_file.upload.click()
            view.flash.assert_message("Error: import processing failed: domain: *")


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1753586])
@pytest.mark.customer_scenario
@pytest.mark.parametrize(
    "import_data",
    [
        DatastoreImport("bz_1753586_user.zip", "bz_1753586_user", None),
        DatastoreImport("bz_1753586_user_locked.zip", "bz_1753586_user_locked", None),
        DatastoreImport("bz_1753586_system.zip", "bz_1753586_system", None),
    ],
    ids=["user", "user_locked", "system"],
)
def test_crud_imported_domains(import_data, temp_appliance_preconfig):
    """
    Bugzilla:
        1753586

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
    """
    # Download datastore file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.datastores)
    file_path = fs.download(import_data.file_name)

    # Import datastore file to appliance
    datastore = temp_appliance_preconfig.collections.automate_import_exports.instantiate(
        import_type="file", file_path=file_path
    )
    domain = datastore.import_domain_from(import_data.from_domain, import_data.to_domain)
    assert domain.exists
    if import_data.file_name == "bz_1753586_system.zip":
        # Imported domains with source - "system" can not be deleted or updated as those are
        # defaults like ManageIQ and RedHat domains.
        view = navigate_to(domain, "Details")
        assert not view.configuration.is_displayed
    else:
        view = navigate_to(domain.parent, "All")
        with update(domain):
            domain.description = fauxfactory.gen_alpha()
        domain.delete()
        view.flash.assert_message(f'Automate Domain "{domain.description}": Delete successful')


@pytest.fixture
def setup_automate_model(appliance):
    """This fixture creates domain, namespace, klass"""
    # names and display names of the domain, namespace, klass needs to be static to match with newly
    # imported datastore.
    domain = appliance.collections.domains.create(
        name="bz_1440226",
        description=fauxfactory.gen_alpha(),
        enabled=True)

    namespace = domain.namespaces.create(
        name="test_name",
        description=fauxfactory.gen_alpha()
    )

    klass = namespace.classes.create(
        name="test_class",
        display_name="test_class_display",
        description=fauxfactory.gen_alpha()
    )
    yield domain, namespace, klass
    klass.delete_if_exists()
    namespace.delete_if_exists()
    domain.delete_if_exists()


@pytest.mark.meta(automates=[1440226])
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1440226.zip", "bz_1440226", None)],
    ids=["datastore_update"],
)
def test_automate_import_attributes_updated(setup_automate_model, import_datastore, import_data):
    """
    Note: We are not able to export automate model using automation. Hence importing same datastore
    which is already uploaded on FTP. So step 1 and 2 are performed manually and uploaded that
    datastore on FTP.

    Bugzilla:
        1440226

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/12h
        tags: automate
        testSteps:
            1. Export an Automate model
            2. Change the description in the exported namespace, class yaml file
            3. Import the updated datastore
            4. Check if the description attribute gets updated
    """
    domain, namespace, klass = setup_automate_model
    view = navigate_to(namespace, "Edit")
    assert view.description.read() == "test_name_desc_updated"
    view = navigate_to(klass, "Edit")
    assert view.description.read() == "test_class_desc"


@pytest.fixture(scope='module')
def local_domain(appliance):
    """This fixture used to create automate domain - Datastore/Domain"""
    # Domain name should be static to match with name of domain imported using rake command
    domain = appliance.collections.domains.create(
        name="bz_1753860", description=fauxfactory.gen_alpha(), enabled=True
    )
    yield domain
    # Tree path of a domain is decided on the basis of it's enabled status, so we are assigning
    # the current value of enabled to make sure the domain is deleted
    domain.enabled = domain.rest_api_entity.enabled
    domain.delete_if_exists()


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1753860])
@pytest.mark.parametrize("file_name", ["bz_1753860.zip"], ids=[''])
def test_overwrite_import_domain(local_domain, appliance, file_name):
    """
    Note: This PR automates this scenario via rake commands. But this RFE is not yet fixed as it has
    bug to apply this scenario via UI.

    Bugzilla:
        1753860

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup:
            1. Create custom domain, namespace, class, instance, method. Do not delete this domain.
            2. Navigate to automation > automate > import/export and export all classes and
               instances to a file
            3. Extract the file and update __domain__.yaml file of custom domain as below:
               >> description: test_desc
               >> enabled: false
               Note: These steps needs to perform manually
        testSteps:
            1. Compress this domain file and import it via UI.
        expectedResults:
            1. Description and enabled status of existing domain should update.
    """
    file = FTPClientWrapper(cfme_data.ftpserver.entities.datastores).get_file(file_name)
    file_path = os.path.join("/tmp", file.name)

    # Download the datastore file on appliance
    assert appliance.ssh_client.run_command(f"curl -o {file_path} ftp://{file.link}").success

    # Rake command to update domain
    cmd = [(
        f"evm:automate:import PREVIEW=false DOMAIN=bz_1753860 IMPORT_AS=bz_1753860 "
        f"ZIP_FILE={file_path} SYSTEM=false ENABLED={enable} OVERWRITE=true"
    ) for enable in ['false', 'true']]

    appliance.ssh_client.run_rake_command(cmd[0])
    view = navigate_to(local_domain.parent, "All")

    # Need to refresh domain to get updates after performing rake command
    view.browser.refresh()

    # Checking domain's enabled status on all page
    assert view.domains.row(name__contains=local_domain.name)["Enabled"].text == "false"

    appliance.ssh_client.run_rake_command(cmd[1])

    # Need to refresh domain to get updates after performing rake command
    view.browser.refresh()

    # Checking domain's enabled status on all page
    assert view.domains.row(name__contains=local_domain.name)["Enabled"].text == "true"
