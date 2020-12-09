"""Tests around the Migration Analytics"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream("5.10"),
    pytest.mark.tier(1),
    test_requirements.migration_analytics
]


@pytest.mark.manual
def test_payload_generation_for_basic_data_without_ssa():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Add VMWare provider
            2. Enable MA
        testSteps:
            1. Navigate to Migration > Migration Analytics
            2. Click on "Get Started"
            3. Click on "Collect Inventory Data"
            4. Select provider
            5. Select "Basic data" and click on "Continue"
        expectedResults:
            1.
            2.
            3.
            4.
            5. Check message - "Inventory collection complete"
    """
    pass


@pytest.mark.manual
def test_payload_generation_with_ssa():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Add VMWare provider
            2. Enable MA
            3. Perform SSA on all VMs
        testSteps:
            1. Navigate to Migration > Migration Analytics
            2. Click on "Get Started"
            3. Click on "Collect Inventory Data"
            4. Select provider
            5. Select "Detailed data" and click on "Continue"
        expectedResults:
            1.
            2.
            3.
            4.
            5. Check message - "Inventory collection complete"
    """
    pass


@pytest.mark.manual
def test_download_payload():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Add VMWare provider
            2. Enable MA
        testSteps:
            1. Navigate to Migration > Migration Analytics
            2. Click on "Get Started"
            3. Click on "Collect Inventory Data"
            4. Select provider
            5. Select "Basic data" and click on "Continue"
            6. Click on "Download"
        expectedResults:
            1.
            2.
            3.
            4.
            5. Report should be downloaded
    """
    pass


@pytest.mark.manual
def test_payload_generation_for_multi_providers():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Add more than one VMWare providers(e.g. vsphere67 and vsphere65)
            2. Enable MA
            3. Perform SSA on all VMs
        testSteps:
            1. Navigate to Migration > Migration Analytics
            2. Click on "Get Started"
            3. Click on "Collect Inventory Data"
            4. Select provider
            5. Select "Detailed data" and click on "Continue"
        expectedResults:
            1.
            2.
            3.
            4.
            5. Check message - "Inventory collection complete"
    """
    pass


@pytest.mark.manual
def test_cancel_payload_generation():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Add VMWare provider
            2. Enable MA
        testSteps:
            1. Navigate to Migration > Migration Analytics
            2. Click on "Get Started"
            3. Click on "Collect Inventory Data"
            4. Select provider and "Basic data" and click on "Continue"
            5. Click on "Cancel"
        expectedResults:
            1.
            2.
            3.
            4.
            5. Check if you came back on inventory data needed page
    """
    pass


@pytest.mark.manual
def test_verify_manifest_version():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Enable MA
        testSteps:
            1. Open link: https://appliance_ip/api/red_hat_migration_analytics
        expectedResults:
            1. See manifest version
    """
    pass


@pytest.mark.manual
def test_confirm_environment_summary_data():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Add VMWare provider
            2. Enable MA
        testSteps:
            1. Navigate to Migration > Migration Analytics
            2. Click on "Get Started"
            3. Check "Environment Summary"
        expectedResults:
            1.
            2.
            3. Check summary data
    """
    pass


@pytest.mark.manual
@pytest.mark.meta(coverage=[1811226])
def test_4k_vms_scan_one_appliance():
    """
    Bugzilla:
        1811226

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
    """
    pass


@pytest.mark.manual
@pytest.mark.meta(coverage=[1810217])
def test_payload_building_with_non_ascii_char():
    """
    Bugzilla:
        1810217

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        setup:
            1. Add a file to SSA profile that includes weird characters.
            2. Sample file used `/usr/java/latest/COPYRIGHT` of Oracle jdk 1.8.0
        testSteps:
            1. Install Oracle JDK 1.8.0 to a VM
            2. Add `/usr/java/latest/COPYRIGHT` file (with content) to the SSA default profile
            3. Run SSA
            4. Go to Migration Analytics page and try to obtain a payload.
        expectedResults:
            1.
            2.
            3.
            4. Page with download link to obtain payload file
    """
    pass


@pytest.mark.manual
@pytest.mark.meta(coverage=[1798054])
def test_manifest_attributes():
    """
    Bugzilla:
        1798054

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        testSteps:
            1. Download the payload file
            2. Check if below attributes are available in the file:
              "cpu_affinity": null,
              "memory_hot_add_enabled": null,
              "cpu_hot_add_enabled": null,
              "cpu_hot_remove_enabled": null,
        expectedResults:
            1. File is downloaded successfully.
            2. All the attributes are available in the file.
    """
    pass


@pytest.mark.manual
@pytest.mark.meta(coverage=[1788730])
def test_payload_download_button():
    """
    Bugzilla:
        1788730

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        testSteps:
            1. Go to Migration Analytics payload download page
        expectedResults:
            1. Download button should available
    """
    pass


@pytest.mark.manual
@pytest.mark.meta(coverage=[1788729])
def test_manifest_import_update():
    """
    Bugzilla:
        1788729

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
    """
    pass
