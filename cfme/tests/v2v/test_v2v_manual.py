"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [test_requirements.v2v, pytest.mark.manual]


@pytest.mark.tier(1)
def test_osp_vmware_67_test_vm_name_with_punycode_characters():
    """
    title: OSP: vmware 67- Test VM name with Punycode characters
    Polarion:
        assignee: sshveta
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        title: Test customize request security group
        testSteps:
            1. Create infrastructure mapping for vmware67 to OSP
            2. Create migration plan with infra map and VM with punycode chars
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration from vmware to OSP
    """
    pass


@pytest.mark.tier(1)
def test_osp_kill_the_v2v_process_in_the_middle_restart_evmserverd_should_resume_migration_pos():
    """
    title: OSP: kill the v2v process in the middle(restart evmserverd) - should
    resume migration post restart

    Polarion:
        assignee: ytale
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        testSteps:
            1. Create infrastructure mapping for vmware67 to OSP
            2. Create migration plan with infra map
            3. Start migration
            4. restart evmserverd on appliance
        expectedResults:
            1.
            2.
            3.
            4. Successful migration from vmware to OSP
    """
    pass


@pytest.mark.tier(2)
def test_osp_migration_plan_with_name_which_has_all_special_character():
    """
    title: OSP: Test migrating a VM using migration plan with name which has all
    special characters

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware67 to OSP
            2. Create migration plan with special chars in name
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration from vmware to OSP
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_flavors_can_be_selected_creating_migration_plan():
    """
    title: OSP: Test flavors can be selected creating migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware67 to OSP
            2. Create migration plan amd choose flavors
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration from vmware to OSP with the selected flavor
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_creating_multiple_migration_plans_with_same_name():
    """
    title: OSP: Test duplicate names in creating migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create two migration plan with same name
        expectedResults:
            1.
            2. Duplicate migration plan name should not be allowed.
    """
    pass


@pytest.mark.tier(2)
def test_osp_vm_name_with_special_characters_can_be_imported():
    """
    title: OSP: Test if VM name with special characters can be imported (It
    should allow such imports)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan and import vm name containing special chars
        expectedResults:
            1.
            2. Importing Vm with special chars in name should be allowed.
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_if_no_password_is_exposed_in_logs_during_migration():
    """
    OSP: Test if no password is exposed in logs during migration

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan
            3. Start migration
        expectedResults:
            1.
            2.
            3. logs should not show password during migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_associated_tags_before_and_after_migration_department_accounting_kind():
    """
    title : OSP: Test associated tags before and after migration
    (Ex: Department:Accounting)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan with a VM tagged to some category
            3. Start migration
        expectedResults:
            1.
            2.
            3. Migrated Vm should have the same tag associated.
    """
    pass


@pytest.mark.tier(2)
def test_osp_vmware65_vm_with_multiple_nics():
    """
    title : OSP: vmware65-Test VM with multiple NICs with single IP (IPv6 to first
    NIC and IPv4 to second)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan with VM with multiple nics
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_retry_plan():
    """
    OSP: Test retry plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan so that it fails
            3. Retry migration
        expectedResults:
            1.
            2.
            3. Migration starts
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_user_can_download_post_migration_ansible_playbook_log():
    """
    title: OSP: Test user can download post migration ansible playbook log

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan and run ansible playbooks
            3. Start migration
        expectedResults:
            1.
            2.
            3. Post migration logs should be downloadable
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_vm_owner_before_and_after_migration_remains_same():
    """
    title: OSP: Test VM owner before and after migration remains same

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan with a VM with some owner
            3. Start migration
        expectedResults:
            1.
            2.
            3. VM owner should remain same
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_migrating_a_vm_which_has_encrypted_disk():
    """
    title : OSP: Test migrating a VM which has encrypted disk

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware to OSP
            2. Create migration plan with a VM with encrypted disk
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_vmware60_test_vm_with_multiple_disks():
    """
    OSP: vmware60-Test VM with multiple Disks

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware60 to OSP
            2. Create migration plan with a VM with multiple disk
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_vmware67_test_vm_with_multiple_disks():
    """
    OSP: vmware60-Test VM with multiple Disks

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware60 to OSP
            2. Create migration plan with a VM with multiple disk
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_policy_to_prevent_source_vm_from_starting_if_migration_is_complete():
    """
    OSP: Test policy to prevent source VM from starting if migration is
    comAplete

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for vmware60 to OSP
            2. Create migration plan with a VM with multiple disk
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_creating_multiple_mappings_with_same_name():
    """
    OSP: Test creating multiple mappings with same name

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping
            2. Create infrastructure with duplicate name
        expectedResults:
            1.
            2.
            3. Duplicate name should not be allowed
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_migrations_with_multi_zonal_setup():
    """
    OSP: Test migrations with multi-zonal setup

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
            1.
            2.
            3.
            4. Successful migration
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_mapping_can_be_created_with_name_including_international_chars():
    """
    OSP: Test mapping can be created with name including international
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
            1. Mapping with international chars
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_archive_completed_migration_plan():
    """
    OSP: Test Archive completed migration plan

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
            1.
            2.
            3.
            4. Archived plan
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_migration_logs_from_conversion_host_can_be_retrieved_from_miq_appliance():
    """
    OSP: Test migration logs from conversion host can be retrieved from
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
            1.
            2.
            3.
            4. Accessible logs in conversion host
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_user_can_run_pre_migration_ansible_playbook():
    """
    OSP: Test user can run pre migration ansible playbook

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
            1.
            2.
            3.
            4. Pre migration playbook runs
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_cpu_cores_and_sockets_pre_vs_post_migration():
    """
    OSP: Test CPU Cores and Sockets Pre vs Post migration

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
            1.
            2.
            3. CPU core and socket should remain same
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_security_group_can_be_selected_while_creating_migration_plan():
    """
    OSP: Test security group can be selected while creating migration plan

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
            1.
            2.
            3. Migration with selected security group completes
    """
    pass


@pytest.mark.tier(2)
def test_osp_test_migration_request_details_page_shows_vms_for_not_started_plans():
    """
    OSP: Test migration request details page shows VMs for not started
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
            1.
            2.
            3. Details page shows VM's
    """
    pass


@pytest.mark.tier(2)
def test_osp_kill_the_v2v_process_in_the_middle_by_rebooting_miq_cfme_appliance_should_resume_():
    """
    OSP: kill the v2v process in the middle- by rebooting miq/cfme
    appliance- should resume migration post restart

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
            4. Reboot appliance
        expectedResults:
            1.
            2.
            3.
            4. Migration should resume.
    """
    pass
