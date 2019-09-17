"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [test_requirements.v2v, pytest.mark.manual]


@pytest.mark.tier(2)
def test_osp_flavors_can_be_selected_creating_migration_plan():
    """
    title: OSP: Test flavors can be selected creating migration plan

    Polarion:
        assignee: ytale
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
def test_osp_if_no_password_is_exposed_in_logs_during_migration():
    """
    title: OSP: Test if no password is exposed in logs during migration

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for Vmware to OSP
            2. Create migration plan
            3. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2.
            3. logs should not show password during migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_retry_plan():
    """
    title: OSP: Test retry plan

    Polarion:
        assignee: ytale
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
def test_osp_user_can_download_post_migration_ansible_playbook_log():
    """
    title: OSP: Test user can download post migration ansible playbook log

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for Vmware to OSP
            2. Create migration plan and run ansible playbooks
            3. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3. Post migration logs should be downloadable
    """
    pass


@pytest.mark.tier(2)
def test_osp_migrations_with_multi_zonal_setup():
    """
    title: OSP: Test migrations with multi-zonal setup

    Polarion:
        assignee: ytale
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
        assignee: ytale
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
        assignee: ytale
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
        assignee: ytale
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
def test_osp_user_can_run_pre_migration_ansible_playbook():
    """
    title: OSP: Test user can run pre migration ansible playbook

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping
            2. Create migration plan and select pre migration logs
            3. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2. Plan created and visible in UI
            3. Pre migration playbook runs
    """
    pass


@pytest.mark.tier(2)
def test_osp_security_group_can_be_selected_while_creating_migration_plan():
    """
    title: OSP: Test security group can be selected while creating migration plan

    Polarion:
        assignee: ytale
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
        assignee: ytale
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
