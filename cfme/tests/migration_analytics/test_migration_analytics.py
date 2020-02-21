"""Tests around the Migration Analytics"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream("5.10"),
    pytest.mark.tier(1),
    test_requirements.migration_analytics
]


@pytest.mark.manual
@pytest.mark.smoke
def test_enable_migration_analytics():
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        startsin: 5.11
        casecomponent: MigrationAnalytics
        testSteps:
            1. Navigate to configuration > Zones > Zone: Default Zone > Server
            2. Click on Advanced tab
            3. Update script as below:
               :prototype:
                    :migration_analytics:
                    :enabled: true
            4. SSH to appliance and restart evmserverd(systemctl restart evmserverd)
        expectedResults:
            1.
            2.
            3.
            4. Check in UI. You will have navigation to Migration > Migration Analytics
    """
    pass


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
