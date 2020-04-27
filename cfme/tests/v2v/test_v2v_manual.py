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


@pytest.mark.ignore_stream('5.10')
@pytest.mark.meta(coverage=[1810091])
@pytest.mark.tier(2)
def test_detection_non_uci_vm():
    """
    title: Test the non uci vm should not detect while configuring conversion host

    Bugzilla:
        1810091
    Polarion:
        assignee: mnadeem
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.11
        testSteps:
            1. Open Tab for configure UCI vm via GUI
        expectedResults:
            1. Check VM in power-off state should not visible
    """
    pass


@pytest.mark.ignore_stream('5.10')
@pytest.mark.meta(coverage=[1804263])
@pytest.mark.tier(2)
def test_mapping_non_admin_project():
    """
    title: Test mapping creation by selecting non-admin project

    Bugzilla:
        1804263
    Polarion:
        assignee: mnadeem
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.11
        testSteps:
            1. Click mapping creation widget
            2. Select non-admin project
        expectedResults:
            1.
            2. Mapping should create successfully
    """
    pass


@pytest.mark.ignore_stream('5.10')
@pytest.mark.meta(coverage=[1719266])
@pytest.mark.tier(2)
def test_vmware_host_wrong_cred():
    """
    title: Test UI throws proper error message for wrong vmware credentials

    Bugzilla:
        1719266
    Polarion:
        assignee: mnadeem
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.11
        testSteps:
            1. Add VMware provider with wrong host credential
            2. Start migration
        expectedResults:
            1.
            2. The GUI throws proper error message for wrong host credential
    """
    pass


@pytest.mark.ignore_stream('5.10')
@pytest.mark.meta(coverage=[1760040])
@pytest.mark.tier(2)
def test_vm_validation_warm_migration():
    """
    title: Test vm validation for warm migration

    Bugzilla:
        1760040
    Polarion:
        assignee: mnadeem
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.11
            testSteps:
            1. Open migration widget
            2. Select vm with snapshots
        expectedResults:
            1.
            2. The GUI will shows the validation message.
    """
    pass


@pytest.mark.ignore_stream('5.10')
@pytest.mark.meta(coverage=[1809035])
@pytest.mark.tier(2)
def test_cancel_migration_state_file_missing():
    """
    title:  Test migration should not stuck and properly gets cancelled if
    virt-v2v-wrapper state file doesn't exist

    Bugzilla:
        1809035
    Polarion:
        assignee: mnadeem
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.11
        testSteps:
            1. Create a CloudForms appliance with region 0, say cf1.example.com
            2. Configuration the conversion host in cf1.example.com
            3. Run a migration on cf1.example.com, the pod will be called conversion-1
            4. Create another appliance with region 0, say cf.example.com
            5. Configuration the conversion host in cf2.example.com
            6. Run a migration on cf2.example.com
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. The pod can't be created as conversion-1 name already exist
    """
    pass
