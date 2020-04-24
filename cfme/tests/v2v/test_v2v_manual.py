"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [test_requirements.v2v, pytest.mark.manual]


@pytest.mark.tier(2)
def test_osp_flavors_can_be_selected_creating_migration_plan():
    """
    title: OSP: Test flavors can be selected creating migration plan

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for Vmware to OSP
            2. Create migration plan amd choose flavors
            3. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3. Successful migration from Vmware to OSP with the selected flavor
    """
    pass


@pytest.mark.tier(2)
def test_osp_retry_plan():
    """
    title: OSP: Test retry plan

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for Vmware to OSP
            2. Create migration plan so that it fails
            3. Retry migration
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3. Migration starts
    """
    pass


@pytest.mark.tier(2)
def test_osp_migrations_with_multi_zonal_setup():
    """
    title: OSP: Test migrations with multi-zonal setup

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create multi zone set up
            2. Create infrastructure mapping
            3. Create migration plan with a VM with multiple disk
            4. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3.
            4. Successful migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_mapping_can_be_created_with_name_including_international_chars():
    """
    title: OSP: Test mapping can be created with name including international
    chars

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping with international chars in name
        expectedResults:
            1. Mapping with international chars created successfully
    """
    pass


@pytest.mark.tier(2)
def test_osp_archive_completed_migration_plan():
    """
    title: OSP: Test Archive completed migration plan

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping
            2. Create migration plan
            3. Start migration
            4. Archive completed plan
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3.
            4. Plan archived successfully
    """
    pass


@pytest.mark.tier(2)
def test_osp_migration_logs_from_conversion_host_can_be_retrieved_from_miq_appliance():
    """
    title: OSP: Test migration logs from conversion host can be retrieved from
    miq appliance

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping
            2. Create migration plan
            3. Start migration
            4. Retrieve logs
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3.
            4. Accessible logs in conversion host
    """
    pass


@pytest.mark.tier(2)
def test_osp_security_group_can_be_selected_while_creating_migration_plan():
    """
    title: OSP: Test security group can be selected while creating migration plan

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping
            2. Create migration plan and select security group
            3. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3. Migration with selected security group completes
    """
    pass


@pytest.mark.tier(2)
def test_osp_migration_request_details_page_shows_vms_for_not_started_plans():
    """
    title: OSP: Test migration request details page shows VMs for not started
    plans

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping
            2. Create migration plan
            3. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3. Details page shows VM
    """
    pass


@pytest.mark.tier(2)
def test_migration_with_alternative_ip_address_for_vmware_host():
    """
    title: Test migration with alternative ip address for vmware host
    plans

    Bugzilla:
        1812685

    Polarion:
        assignee: nachandr
        casecomponent: V2V
        initialEstimate: 1/4h
        startsin: 5.11
        testSteps:
            1. Update transformation ip address for vmware host through Rails console
            2. Start migration
        expectedResults:
            1. Alternative ip address should be used for migration
            2. Migration should succeed
    """
    pass


@pytest.mark.tier(3)
def test_migration_for_vm_without_ip_address():
    """
    title: Test migration for VM without IP address
    plans

    Bugzilla:
        1814876

    Polarion:
        assignee: nachandr
        casecomponent: V2V
        initialEstimate: 1/4h
        startsin: 5.11
        testSteps:
            1. Disconnect VM NIC in vCenter so that the VM doesn't have an IP address
            2. Start migration
        expectedResults:
            1. Migration should succeed
    """
    pass
