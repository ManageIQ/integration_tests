# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream('5.10', 'upstream')]


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_with_rhel_75_last_time_74():
    """
    OSP: vmware65-Test VM migration with RHEL 7.5 (last time 7.4)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration with RHEL 7.5 (last time 7.4)
    """
    pass


@pytest.mark.manual
def test_ec2_refresh_with_stack_without_parameters():
    """
    1) Add cloudformation stack without parameters(https://s3-us-
    west-2.amazonaws.com/cloudformation-templates-us-
    west-2/Managed_EC2_Batch_Environment.template  )
    2) Add ec2 provider with cloudformation stack without parameters
    3) Wait for refresh - it should be refreshed successfully without
    errors

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/5h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_nor_cpu_values_correct_vsphere6():
    """
    NOR cpu values are correct.
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays correct values for CPU and CPU
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured:
    The Average reflects the most common value obtained during the past 30
    days" worth of captured metrics.
    The High and Low reflect the range of values obtained ~85% of the time
    within the past 30 days.
    The Max reflects the maximum value obtained within the past 30 days.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_nor_cpu_values_correct_rhv41():
    """
    NOR CPU values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_status_of_a_task_via_api_with_evmrole_administrator():
    """
    Bugzilla:
        1535962

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        tags: rbac
        title: Test status of a task via API with EvmRole_administrator
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_cluster_vsphere6():
    """
    test_crosshair_op_cluster[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_cluster_vsphere65():
    """
    Requires:
    C&U enabled Vsphere-65 appliance.
    Steps:
    1. Navigate to Clusters [Compute > infrastructure>Clusters]
    2. Select any available cluster
    3. Go for utilization graphs [Monitoring > Utilization]
    4. Check data point on graphs ["CPU", "VM CPU state", "Memory", "Disk
    I/O", "N/w I/O", "Host", "VMs"] using drilling operation on the data
    points.
    5.  check "chart", "timeline" and "display" options working properly
    or not.

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_field_zone_description_special():
    """
    Special Chars in description

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_remove_ec2():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the ec2 proxy settings.  For this test you want to create an
    default proxy, verified it worked, and then remove the proxy and
    verify it didn"t use a proxy
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: proxy
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        setup: I think the best way to do this one is start with a bad proxy value,
               get the connection error, and then remove the proxy values and make
               sure it starts connecting again.  I"ll have to see if there is a log
               value we can look at.  Otherwise, you need to shutdown the proxy
               server to be absolutely sure.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_remove_gce():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the ec2 proxy settings.  For this test you want to create an
    default proxy, verified it worked, and then remove the proxy and
    verify it didn"t use a proxy
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: proxy
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        setup: I think the best way to do this one is start with a bad proxy value,
               get the connection error, and then remove the proxy values and make
               sure it starts connecting again.  I"ll have to see if there is a log
               value we can look at.  Otherwise, you need to shutdown the proxy
               server to be absolutely sure.
               You can also remove by setting host to false
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_verify_httpd_only_running_when_roles_require_it():
    """
    Provision preconfigured appliance A.
    Provision non-preconfigured appliance B.
    On appliance A, stop server processes:
    # appliance_console
    > Stop EVM Server Processes > Y
    On appliance B, join to appliance A:
    # appliance_console
    > Configure Database > Fetch key from remote machine
    > enter IP address of appliance A
    > root > smartvm
    > /var/www/miq/vmdb/certs/v2_key
    > Join Region in External Database
    > enter IP address of appliance A
    > 5432 > vmdb_production > root > smartvm
    On appliance A, restart server processes:
    > Start EVM Server Processes > Y
    Log in the web UI on appliance A, and disable roles on appliance B
    that require httpd:
    Administrator > Configuration
    > click on appliance B in accordion menu"s list of servers
    > under Server Control, disable all server roles > Save
    On appliance B, verify that the httpd service stops:
    # systemctl status httpd
    ● httpd.service - The Apache HTTP Server
    Loaded: loaded (/usr/lib/systemd/system/httpd.service; disabled;
    vendor preset: disabled)
    Active: inactive (dead) since Fri 2018-01-12 10:57:29 EST; 22s ago
    [...]
    Enable one of the following roles, and verify that httpd restarts:
    Cockpit, Embedded Ansible, User Interface, Web Services, Websocket

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify httpd only running when roles require it
    """
    pass


@pytest.mark.manual
def test_appliance_terminates_unresponsive_worker_process():
    """
    If a queue message consumes significant memory and takes longer than
    the 10 minute queue timeout, the appliance will kill the worker after
    the stopping_timeout.
    Steps to test (see BZ below, comments 30 and 31).

    Bugzilla:
        1395736

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
        title: Appliance terminates unresponsive worker process
    """
    pass


@pytest.mark.manual
def test_osp_test_saving_migration_plan_after_creation():
    """
    OSP: Test saving migration plan after creation

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test saving migration plan after creation
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_with_really_long_name_upto_64_chars_worked_not_65_char():
    """
    OSP: vmware60-Test VM migration with really long name(Upto 64 chars
    worked, not 65 chars)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration with really long name(Upto
               64 chars worked, not 65 chars)
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_with_rhel_69():
    """
    OSP: vmware60-Test VM migration with RHEL 6.9

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration with RHEL 6.9
    """
    pass


@pytest.mark.manual
def test_osp_test_datastore_allocation_summary_before_and_after_migration_disk_memory():
    """
    OSP: Test Datastore Allocation Summary before and after migration
    (Disk, Memory)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test Datastore Allocation Summary before and after migration (Disk, Memory)
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_with_windows_2016_server():
    """
    OSP: vmware67-Test VM migration with Windows 2016 server

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration with Windows 2016 server
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_external_database_appliance():
    """
    Configure appliance to use external DB

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_data_processor():
    """
    C & U Data Processor (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_stack_service_vm_detail_page_should_show_correct_data():
    """
    Bugzilla:
        1467569

    Polarion:
        assignee: sshveta
        casecomponent: SelfServiceUI
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : Stack Service VM detail page should show correct data
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
@pytest.mark.tier(2)
def test_retire_infra_vms_folder():
    """
    test the retire funtion of vm on infra providers, at least two vm,
    retire now button vms page

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_infrastructure_hosts_icons_states():
    """
    Requirement: Added a RHEVM provider
    Then do in console:
    su - postgres
    psql
    vmdb_production
    UPDATE hosts SET power_state = "preparing_for_maintenance" WHERE
    name="NAME OF THE TESTED HOST";
    UPDATE hosts SET power_state = "maintenance" WHERE name="NAME OF THE
    TESTED HOST";
    UPDATE hosts SET power_state = "unknown" WHERE name="NAME OF THE
    TESTED HOST";
    UPDATE hosts SET power_state = "on" WHERE name="NAME OF THE TESTED
    HOST";
    UPDATE hosts SET power_state = "off" WHERE name="NAME OF THE TESTED
    HOST";
    Between every update check state icon in Compute -> Infrastructure ->
    Hosts -> Host quadicon and Compute -> Infrastructure -> Hosts ->
    Summary of the host

    Polarion:
        assignee: anikifor
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
def test_ec2_public_images():
    """
    1) Set
    :ems_refresh:
    :ec2:
    :get_public_images: true
    2) Add an ec2 provider
    3) Wait for its refresh(It can take more than 30 minutes)
    4) Refresh should be successful and there should be more than 100k ec2
    images

    Polarion:
        assignee: mmojzis
        caseimportance: critical
        initialEstimate: 2/3h
        casecomponent: Cloud
    """
    pass


@pytest.mark.manual
def test_validate_chargeback_cost_weekly_rate_network_cost():
    """
    Validate network I/O used cost in a daily Chargeback report by
    assigning weekly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_network_cost():
    """
    Validate network I/O used cost  for a tiered rate with fixed and
    variable components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
def test_validate_chargeback_cost_monthly_rate_disk_cost():
    """
    Validate disk I/O used cost in a daily Chargeback report by assigning
    monthly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_monthlyreport_hourly_rate_network_cost():
    """
    Validate network I/O used cost in a monthly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_weeklyreport_hourly_rate_disk_cost():
    """
    Validate disk I/O used cost in a weekly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
def test_validate_chargeback_cost_monthly_rate_network_cost():
    """
    Validate network I/O used cost in a daily Chargeback report by
    assigning monthly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
def test_validate_chargeback_cost_weekly_rate_disk_cost():
    """
    Validate disk I/O used cost in a dailyy Chargeback report by assigning
    weekly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_validate_chargeback_cost_resource_allocation_cpu_allocated():
    """
    Validate CPU allocated cost in a Chargeback report based on resource
    allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_weekly_rate_cpu_cost():
    """
    Validate CPU usage cost in a daily Chargeback report by assigning
    weekly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_cpu_cost():
    """
    Validate CPU usage cost for a tiered rate with fixed and variable
    components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_validate_chargeback_cost_resource_allocation_storage_allocated():
    """
    Validate storage allocated cost in a Chargeback report based on
    resource allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_monthlyreport_hourly_rate_disk_cost():
    """
    Validate disk I/O used cost in a monthly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_weeklyreport_hourly_rate_cpu_cost():
    """
    Validate CPU usage cost in a weekly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_monthlyreport_hourly_rate_memory_cost():
    """
    Validate memory usage cost in a monthly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
def test_validate_chargeback_cost_monthly_rate_cpu_cost():
    """
    Validate CPU usage cost in a daily Chargeback report by assigning
    monthly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_weekly_rate_memory_cost():
    """
    Validate memory usage cost in a daily Chargeback report by assigning
    weekly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_weeklyreport_hourly_rate_memory_cost():
    """
    Validate memory usage cost in a weekly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_weeklyreport_hourly_rate_network_cost():
    """
    Validate network I/O used cost in a weekly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_disk_cost():
    """
    Validate disk I/O used cost for a tiered rate with fixed and variable
    components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_validate_chargeback_cost_resource_allocation_memory_allocated():
    """
    Validate memory allocated cost in a Chargeback report based on
    resource allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_monthlyreport_hourly_rate_cpu_cost():
    """
    Validate CPU usage cost in a monthly Chargeback report

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_validate_chargeback_cost_tiered_rate_fixedvariable_memory_cost():
    """
    Validate memory usage cost  for a tiered rate with fixed and variable
    components

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
def test_validate_chargeback_cost_monthly_rate_memory_cost():
    """
    Validate memory usage cost in a daily Chargeback report by assigning
    monthly rate

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
def test_osp_vmware_67_test_vm_name_with_punycode_characters():
    """
    OSP: vmware 67- Test VM name with Punycode characters

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware 67- Test VM name with Punycode characters
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_prov_from_service_survey_ansible_tower_310():
    """
    1) Navigate to Configuration -> Configuration management -> Ansible
    Tower job templates.
    - click on job template -> Configuration -> Create service dialog from
    this job template -> give it name
    (Job template with preconfigured Survey must be used!!!)
    2) Create new catalog Item
    - Catalog Item type: AnsibleTower
    - name your catalog item
    - Display in catalog: checked
    - catalog: pick your catalog
    - Dialog: Tower_dialog
    - Provider: Ansible Tower .....
    3) Order service and fill in service details

    Polarion:
        assignee: nachandr
        casecomponent: Provisioning
        initialEstimate: 1h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
def test_osp_test_executing_previously_created_migration_plan():
    """
    OSP: Test executing previously created migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test executing previously created migration plan
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_report_weekly():
    """
    Verify that 1)weekly chargeback reports can be generated and 2)that
    the report contains relevant data for the relevant period.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_osp_test_immediately_migration_after_migration_plan_creation():
    """
    OSP: Test immediately migration after migration plan creation

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test immediately migration after migration plan creation
    """
    pass


@pytest.mark.manual
@test_requirements.replication
def test_distributed_add_provider_to_remote_zone():
    """
    Adding a provider from the global region to a remote zone.

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_that_non_admin_users_can_view_catalog_items_in_ssui():
    """
    Verify user with a non-administrator role can login to the SSUI and
    view catalog items that are tagged for them to see

    Bugzilla:
        1465642

    Note: in order for this to work, all ownership limitations must be
    removed.

    Polarion:
        assignee: apagac
        casecomponent: SelfServiceUI
        initialEstimate: 1/2h
        setup: Create a user account with a non-admin role w/ any necessary tags,
               "View Catalog Items" permissions and SSUI access
               Create a catalog item that is visible to the user
        title: Test that non-admin users can view catalog items in SSUI
        testSteps:
            1. Login to the SSUI as a non-admin user
            2. Attempt to view all catalog items the user has access to
        expectedResults:
            1. SSUI login
            2.
    """
    pass


@pytest.mark.manual
def test_osp_kill_the_v2v_process_in_the_middle_restart_evmserverd_should_resume_migration_pos():
    """
    OSP: kill the v2v process in the middle(restart evmserverd) - should
    resume migration post restart

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: kill the v2v process in the middle(restart evmserverd)
               - should resume migration post restart
    """
    pass


@pytest.mark.manual
def test_storage_ebs_volume_crud():
    """
    Requires:
    test_storage_ebs_added
    Steps to test:
    Create:
    1. Go to Storage -> Block Storage -> Volumes
    2. Add a new cloud volume
    3.Form to fill:
    ec2 EBS Storage Manager
    us-east-1
    volume_test
    Magnetic
    6
    Encryption off
    4. Add
    Read:
    1. Select "volume_test" and go to its summary
    Edit:
    1. Configuration -> Edit this Cloud Volume
    2. Change volume name from "volume_test" to "volume_edited_test"
    3. Select "volume_edited_test" in Block Volume list and go to its
    summary
    Delete:
    1. Configuration -> Delete this Cloud Volume
    2. Check whether volume was deleted

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        startsin: 5.8
        casecomponent: Cloud
    """
    pass


@pytest.mark.manual('manualonly')
def test_ec2_deploy_cfme_image():
    """
    Bugzilla:
        1413835
    Requirement: CFME image imported as AMI in EC2 environment - should be
    imported automatically with every build
    1) Deploy appliance:
    c4.xlarge instance type
    default vpc network
    Two disks: one default 41GB, one additional 10GB
    Security group with open port 22 & 443 to world
    select appropriate private key
    2) Associate instance with Elastic IP
    3) Configure database using appliance_console
    4) Start evmserverd
    5) CFME appliance should work

    Polarion:
        assignee: mmojzis
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 4h
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_with_really_long_name_upto_64_chars_worked_not_65_char():
    """
    OSP: vmware67-Test VM migration with really long name(Upto 64 chars
    worked, not 65 chars)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration with really long name(Upto
               64 chars worked, not 65 chars)
    """
    pass


@pytest.mark.manual
def test_osp_test_migrating_a_vm_using_migration_plan_with_name_which_has_all_special_characte():
    """
    OSP: Test migrating a VM using migration plan with name which has all
    special characters

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test migrating a VM using migration plan with name
               which has all special characters
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_field_zone_description_long():
    """
    When creating a new zone, the description can be up to 50 characters
    long, and displays correctly after saving.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
def test_osp_test_flavors_can_be_selected_creating_migration_plan():
    """
    OSP: Test flavors can be selected creating migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test flavors can be selected creating migration plan
    """
    pass


@pytest.mark.manual
def test_osp_test_migration_plan_filtering_for_plans_table_list_on_overview_and_details_page():
    """
    OSP: Test Migration Plan Filtering for plans table/list on overview
    and details page

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test Migration Plan Filtering for plans table/list on
               overview and details page
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
def test_retirement_date_uses_correct_time_zone():
    """
    Bug 1565128 - Wrong timezone when selecting retirement time

    Bugzilla:
        1565128

    After saving VM retirement date/time (using both "Specific Date and
    Time" and "Time Delay from Now" options), the displayed Retirement
    Date has the correct date and time-zone appropriate time.

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
        startsin: 5.9
        title: Retirement date uses correct time zone
    """
    pass


@pytest.mark.manual
@test_requirements.replication
def test_distributed_zone_add_provider_to_nondefault_zone():
    """
    Can a new provider be added the first time to a non default zone.

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_azone_cpu_usage_gce():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(1)
def test_azone_cpu_usage_azure():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_orchestration_link_mismatch():
    """

    Bugzilla:
        1601523

    Polarion:
        assignee: sshveta
        casecomponent: Stack
        caseimportance: medium
        initialEstimate: 1/4h
        title: orchestration link mismatch
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_service_chargeback_multiple_vms():
    """
    Validate Chargeback costs for a service with multiple VMs

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_with_windows_7():
    """
    OSP: vmware67-Test VM migration with Windows 7

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration with Windows 7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_crosshair_op_azone_azure():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_crosshair_op_azone_gce():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_crosshair_op_azone_ec2():
    """
    test_crosshair_op_azone[ec2]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_edit_provider_request_task():
    """
    In this test we will try to edit a provider request using POST
    request.
    Note: Only Option field can be edited

    Polarion:
        assignee: pvala
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Rest
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_delete_occupied():
    """
    Delete Zone that has appliances in it.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_can_add_child_tenant_to_tenant():
    """
    Bugzilla:
        1387088
    1. Go to Configuration -> Access Control
    2. Select a Tenant
    3. Use "Configuration" Toolbar to navigate to "Add child Tenant to
    this Tenant"
    4. Fill the form in:
    Name: "test_tenant"
    Description: "test_tenant"
    Then select "Add"
    Child tenant should be displayed under Parent Tenant

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/10h
        tags: rbac
    """
    pass


@pytest.mark.manual
def test_osp_test_in_progress_migrations_can_be_cancelled():
    """
    OSP: Test in-progress Migrations can be cancelled

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test in-progress Migrations can be cancelled
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_host_tagged_crosshair_op_vsphere65():
    """
    Required C&U enabled application:1. Navigate to host C&U graphs
    2. select Group by option with suitable VM tag
    3. try to drill graph for VM

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_host_tagged_crosshair_op_vsphere6():
    """
    Required C&U enabled application:1. Navigate to host C&U graphs
    2. select Group by option with suitable VM tag
    3. try to drill graph for VM

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_host_tagged_crosshair_op_vsphere55():
    """
    Required C&U enabled application:1. Navigate to host C&U graphs
    2. select Group by option with suitable VM tag
    3. try to drill graph for VM

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_verify_only_groups_with_ssui_access_can_access_the_ssui_when_switching_groups():
    """
    When a user is a member of two or more groups and one of the groups
    does not have access to the SSUI, verify that the group w/o SSUI does
    not stay logged in after switching groups.

    Polarion:
        assignee: apagac
        casecomponent: SelfServiceUI
        caseimportance: critical
        initialEstimate: 1/6h
        setup: Create a user that is a member of two more groups with one group
               having SSUI access and the other group having SSUI access disabled.
        startsin: 5.9
        tags: rbac
        title: Verify only groups with SSUI access can access the SSUI when switching groups
        testSteps:
            1. Login to the SSUI
            2. Switch to the group that doesn"t have SSUI access
        expectedResults:
            1. Login successful
            2. Automatically logged out of the SSUI
    """
    pass


@pytest.mark.manual
def test_osp_edit_migration_plan_before_and_after_deletion_soon_in_510():
    """
    OSP: Edit migration plan before and after deletion (soon in 5.10)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Edit migration plan before and after deletion (soon in 5.10)
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_with_windows_7():
    """
    OSP: vmware60-Test VM migration with Windows 7

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration with Windows 7
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_volume_backup_restore_openstack():
    """
    Requires:
    test_storage_volume_backup[openstack]
    1 . Go back to the summary page of the respective volume.
    2 . Restore Volume [configuration > Restore from backup of this cloud
    volume > select cloud volume backup]
    3. check in Task whether restored or not.

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_with_windows_2012_server():
    """
    OSP: vmware60-Test VM migration with Windows 2012 server

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration with Windows 2012 server
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_instance():
    """
    Instance CREATE
    Instance RUNNING
    Instance STOPPED
    Instance UPDATE
    Instance DELETE - or - Instance TERMINATE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_verify_that_changing_groups_while_in_ssui_updates_dashboard_items():
    """
    Verify that switching Groups in SSUI changes the dashboard items to
    match the new groups permissions

    Polarion:
        assignee: apagac
        casecomponent: SelfServiceUI
        initialEstimate: 1/4h
        setup: Create a user with two or more groups with access to the SSUI. The
               groups should have role permissions that grant access to different
               features so you can easily see that the dashboard is updated
               appropriately.
        startsin: 5.9
        tags: rbac
        title: Verify that changing groups while in SSUI updates dashboard items
        testSteps:
            1. Login to the SSUI
            2. Switch to another group
            3. Check that dashboard items are updated appropriately
        expectedResults:
            1. Login successful
            2. Group switch successful
            3. Dashboard items are updated from to reflect that access of the new group
    """
    pass


@pytest.mark.manual
def test_osp_vmware_65_test_vm_name_with_punycode_characters():
    """
    OSP: vmware 65- Test VM name with Punycode characters

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware 65- Test VM name with Punycode characters
    """
    pass


@pytest.mark.manual
@test_requirements.tower
def test_config_manager_accordion_tree():
    """
    Make sure there is accordion tree, once Tower is added to the UI.

    Bugzilla:
        1560552

    Polarion:
        assignee: nachandr
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_service_chargeback_bundled_service():
    """
    Validate Chargeback costs for a bundled service

    Polarion:
        assignee: nachandr
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_datastore():
    """
    Verify bottleneck events from host

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_ec2_api_filter_limit():
    """
    Bugzilla:
        1612086

    The easiest way to simulate AWS API Limit for > 200 items is to enable
    and disable public images:
    Requirement: Have an ec2 provider
    1) Enable public images for ec2 in Advanced Settings
    2) Wait for public images to be refreshed
    3) Disable public images for ec2 in Advanced Settings
    4) Wait for public images to be refreshed (cleared)

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1 1/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_host_credentials_web():
    """
    Validate that web connections to the host can be created.

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_from_nfs_storage_in_vmware_to_nfs_on_osp():
    """
    OSP: vmware67-Test VM migration from NFS Storage in VMware to NFS on
    OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration from NFS Storage in VMware to NFS on OSP
    """
    pass


@pytest.mark.manual
def test_group_quota_via_ssui():
    """
    Polarion:
        assignee: sshveta
        initialEstimate: 1/4h
        casecomponent: SelfServiceUI
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_cluster_graph_by_vm_tag_vsphere65():
    """
    test_cluster_graph_by_vm_tag[vsphere65]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_cluster_graph_by_vm_tag_vsphere6():
    """
    test_cluster_graph_by_vm_tag[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_can_add_project_to_tenant():
    """
    Bugzilla:
        1387088

    1. Go to Configuration -> Access Control
    2. Select a Tenant
    3. Use "Configuration" Toolbar to navigate to "Add Project to this
    Tenant"
    4. Fill the form in:
    Name: "test_project"
    Description: "test_project"
    Then select "Add"
    Project should be displayed under Parent Tenant

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/10h
        tags: rbac
    """
    pass


@pytest.mark.manual
def test_osp_test_if_non_csv_files_can_be_imported():
    """
    OSP: Test if non-csv files can be imported

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test if non-csv files can be imported
    """
    pass


@pytest.mark.manual
@test_requirements.satellite
def test_no_rbac_warnings_in_logs_when_viewing_satellite_provider():
    """
    RBAC-related warnings logged when viewing Satellite provider in web UI

    Bugzilla:
        1565266
    1.) Add Satellite provider.
    2.) Click on items under Providers accordion.
    3.) View evm.log. No WARN-level messages should be logged.
    [----] W, [2018-04-09T14:09:19.654859 #13384:84e658]  WARN -- :
    MIQ(Rbac::Filterer#lookup_method_for_descendant_class) could not find
    method name for ConfiguredSystem::ConfiguredSystem

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/15h
        title: No RBAC warnings in logs when viewing Satellite provider
    """
    pass


@pytest.mark.manual
def test_ec2_create_sns_topic():
    """
    Requires: No SNS topic for tested region
    1) Add an ec2 provider with tested region
    2) Wait 3 minutes
    3) Check SNS topic for this region in AWS Console

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_provider():
    """
    Verify bottleneck events from providers

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_osp_test_multi_host_migration_execution_if_more_than_one_host_present_migration_of_mu():
    """
    OSP: Test Multi-host migration execution, if more than one host
    present, migration of muliple VMs should be spread across all
    available hosts

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test Multi-host migration execution, if more than one
               host present, migration of muliple VMs should be spread
               across all available hosts
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_prov_from_service_limit_ansible_tower_310():
    """
    1) Navigate to Configuration -> Configuration management -> Ansible
    Tower job templates.
    - click on job template -> Configuration -> Create service dialog from
    this job template -> give it name
    2) Create new catalog Item
    - Catalog Item type: AnsibleTower
    - name your catalog item
    - Display in catalog: checked
    - catalog: pick your catalog
    - Dialog: Tower_dialog
    - Provider: Ansible Tower .....
    3) Order service with limit

    Polarion:
        assignee: nachandr
        casecomponent: Provisioning
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_osp_test_creating_multiple_migration_plans_with_same_name():
    """
    OSP: Test flavors can be selected creating migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test creating multiple migration plans with same name
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(3)
def test_distributed_migrate_embedded_ansible_role():
    """
    Ansible role failsover/migrates when active service fails

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/4h
        setup: 1. Configure a 2 server installation (same region + zone)
               2. Assign the embedded ansible role to both servers
               5. Find the server the role is active on (for me it was Server 1 and I
               used the diagnostics tab Zone view)
               6. run `systemctl stop evmserverd` on Server 1
               7. Observe that the role is started on Server 2
    """
    pass


@pytest.mark.manual
def test_osp_test_if_vm_name_with_special_characters_can_be_imported_it_should_allow_such_impo():
    """
    OSP: Test if VM name with special characters can be imported (It
    should allow such imports)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test if VM name with special characters can be imported
               (It should allow such imports)
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_usage_memory():
    """
    Validate cost for memory usage for a VM in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_allocation_storage():
    """
    Validate cost for VM storage allocation in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_usage_disk():
    """
    Validate cost for disk io for a VM in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_usage_storage():
    """
    Validate cost for storage usage for a VM in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_usage_cpu():
    """
    Validate cost for CPU usage for a VM in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_allocation_memory():
    """
    Validate cost for VM memory allocation in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_usage_network():
    """
    Validate cost for network io for a VM  in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_allocation_cpu():
    """
    Validate cost for VM CPU allocation in a weekly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_floating_ip():
    """
    #AWS naming is Elastic IP
    Classic Floating IP Allocate
    VPC Floating IP Allocate
    Classic Floating IP Allocate to Instance (Check both IP and Instance)
    Classic Floating IP Allocate to Network Port (Check both IP and Port)
    VPC Floating IP Allocate to Instance (Check both IP and Instance)
    VPC Floating IP Allocate to Network Port (Check both IP and Port)
    Floating IP UPDATE
    Floating IP DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_host_graph_by_vm_tag_vsphere6():
    """
    test_host_graph_by_vm_tag[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_host_graph_by_vm_tag_vsphere65():
    """
    Requires:
    C&U enabled Vsphere-65 appliance.
    Steps:
    1. Navigate to Host [Compute > infrastructure>Hosts]
    2. Select any available host
    3. Go for utilization graphs [Monitoring > Utilization]
    4. For hourly "Group by"  select VM tag
    5. For Daily "Group by" select VM tag

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_test_ssh_creds_can_be_added_while_adding_osp_provider():
    """
    OSP: Test SSH Creds can be added while adding OSP provider

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test SSH Creds can be added while adding OSP provider
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_network():
    """
    #AWS naming is VPC
    Network CREATE
    Network UPDATE
    Network DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_candu_graphs_vm_compare_host_vsphere6():
    """
    test_candu_graphs_vm_compare_host[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_candu_graphs_vm_compare_host_vsphere65():
    """
    test_candu_graphs_vm_compare_host[vsphere65]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_sdn_nsg_firewall_rules_azure():
    """
    Bugzilla:
        1520196

    1. Add Network Security group on Azure with coma separated port ranges
    `1023,1025` rule inbound/outbound ( ATM this feature is not allowed in
    East US region of Azure - try West/Central)
    2. Add such Azure Region into CFME
    3. Refresh provider
    4. Open such NSG in CFME and check that ports from 1) do present in
    the UI as Firewall rules

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_provider_specific_vm():
    """
    Steps:
    1) Add multiple provider
    2) Check for the vms specific to a provider
    2) Repeat it for all the providers

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(1)
def test_utilization_utilization_graphs():
    """
    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        initialEstimate: 1/4h
        testSteps:
            1. Enable C&U
            2. Wait until data will be collected
            3. Go to Optimize/Utilization
        expectedResults:
            1.
            2.
            3. Verify that all graphs shows correctly
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_field_zone_name_special():
    """
    When creating a new zone, special characters can be used in the name,
    including leading and trailing characters, and the name displays
    correctly in the web UI after saving.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_delete_orchestration_template_in_use():
    """
    Delete orchestration template in use

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/16h
        setup: Create a orchestration template and provision a stack from it .
               Delete the template
        startsin: 5.5
        title: Delete orchestration template in use
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_service_chargeback_retired_service():
    """
    Validate Chargeback costs for a retired service

    Polarion:
        assignee: nachandr
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_network_router():
    """
    #AWS naming is Route Table
    Network Router CREATE
    Network Router DELETE
    Network Router UPDATE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_object_store_object_remove():
    """
    Requirs:
    OpenstackProvider
    1) Navigate to Object Store Object [Storage > Object Storage > Object
    Store Objects]
    2) Select objects for removal
    3) Remove [Configuration > Remove Object Storage Objects from
    Inventory]
    4) Verify object removed or not

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_osp_test_networking_before_and_after_migration_mac_address():
    """
    OSP: Test networking before and after migration (MAC Address)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test networking before and after migration (MAC Address)
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_puma_server():
    """
    From a bugPuma, by default is a threaded web server, which means each
    http(s) request will be handled in a new thread. Since Rails" database
    connection pool reserves connections to threads, it"s possible to
    exhaust the connection pool with enough web requests spinning up new
    puma threads. Thin, by contrast, still processes each request in a
    single thread by default. While this is usually slower, you don"t have
    the issues of multiple threads in flight at the same time.We should
    make puma the default web server but have an easy option to switch to
    thin in case there are thread issues with puma.To change the web
    server, change puma to thin in the advanced configuration:
    :server:
    :rails_server: pumaNote: Testers/users, the proctitle for
    UI/Webservice and web socket workers will
    look different in ps, top, etc. if you use thin instead of puma. Puma
    configures
    it"s own proctitle and we configure the parts that we can. Thin does
    not, so it
    will look like all the other workers.
    For example:
    thin:
    43177 ttys002 0:08.20 MIQ: MiqUiWorker id: 158, uri:
    http://0.0.0.0:3000
    puma:
    43871 ttys004 0:00.68 puma 3.3.0 (tcp://0.0.0.0:3000) [MIQ: Web Server
    Worker]

    Polarion:
        assignee: jhenner
        casecomponent: WebUI
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_session_purging_occurs_only_when_session_store_is_sql():
    """
    If Settings > server > session_store is set to "sql", then evm.log
    shows that the Session.check_session_timeout worker gets regularly
    queued (at a regular interval of Settings > workers > worker_base >
    schedule_worker > session_timeout_interval). If session_store is not
    set to "sql", then the worker does not get scheduled.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/10h
        title: Session purging occurs only when session_store is sql
    """
    pass


@pytest.mark.manual
@test_requirements.satellite
def test_satellite_host_groups_show_up_as_configuration_profiles_satellite_62():
    """
    For the Satellite provider satellite_62, both the centos and fedora-
    cloud configuration profiles show up in Configuration > Manage, in the
    accordion menu under All Configuration Manager Providers > Red Hat
    Satellite Providers > satellite_62 Configuration Manager.

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/15h
        title: Satellite host groups show up as Configuration Profiles [satellite_62]
    """
    pass


@pytest.mark.manual
def test_osp_test_if_no_password_is_exposed_in_logs_during_migration():
    """
    OSP: Test if no password is exposed in logs during migration

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test if no password is exposed in logs during migration
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_vm_request_approval_by_user_in_different_group():
    """
    Bugzilla:
        1545395

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
        title: Test VM request approval by user in different group
    """
    pass


@pytest.mark.manual
@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_host():
    """
    Verify bottleneck events from host

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_mixed_appliance_ip_versions():
    """
    IPv6 and IPv4 appliances

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1h
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_network_port():
    """
    #AWS naming is Network Interface
    Network port CREATE
    Network port UPDATE
    Assign private IP
    Unassign private IP
    Network port DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_from_ubuntu():
    """
    OSP: vmware60-Test VM migration from ubuntu

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration from ubuntu
    """
    pass


@pytest.mark.manual
def test_rhn_mirror_role_packages():
    """
    Test the RHN mirror role by adding a repo and checking if the contents
    necessary for product update got downloaded to the appliance

    Polarion:
        assignee: jkrocil
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 3/4h
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_from_nfs_storage_in_vmware_to_osp():
    """
    OSP: vmware65-Test VM migration from NFS Storage in VMware to iSCSI on
    OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration from NFS Storage in VMware to OSP
    """
    pass


@pytest.mark.manual
def test_osp_test_delete_infra_mapping():
    """
    OSP: Test delete infra mapping

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test delete infra mapping
    """
    pass


@pytest.mark.manual
def test_storage_ebs_snapshot_create():
    """
    Requires: An ec2 provider
    1) Create a block storage volume
    2) Go to its summary
    3) Select Configuration in toolbar and click on Create a Snapshot of
    this Cloud Volume
    4) Go to Storage -> Block Storage -> Snapshots
    5) Check whether newly created snapshot appears

    Polarion:
        assignee: mmojzis
        caseimportance: medium
        casecomponent: Cloud
        initialEstimate: 1/5h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(3)
def test_distributed_delete_offline_worker_appliance():
    """
    Steps to Reproduce:
    have 3 servers .
    Shutdown one server. This become inactive.
    go to WebUI > Configuration > Diagnostics > Select "Zone: Default
    zone" > Select worker > Configuration > Delete

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_playbook_with_already_existing_dialogs_name():
    """
    Bugzilla:
        1449345

    Polarion:
        assignee: sshveta
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        title: Test Playbook with already existing dialog's name
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
@pytest.mark.tier(2)
def test_retire_cloud_vms_date_folder():
    """
    test the retire funtion of vm on cloud providers, at leat two vm, set
    retirement date button from vms page(without notification)

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_utilization_provider():
    """
    Verify гutilication data from providers

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 1/8h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_pg_stat_activity_view_in_postgres_should_show_worker_information():
    """
    pg_stat_activity view in postgres should show worker information.
    Bug 1445928 - It is impossible to identify the source
    process/appliance for each connection in pg_stat_activity

    Bugzilla:
        1445928

    # su - postgres
    # psql vmdb_production
    vmdb_production=# select pid, application_name from pg_stat_activity;
    pid  |                        application_name
    -------+--------------------------------------------------------------
    ---
    17109 | MIQ 16946 Server[2], default[2]
    17274 | MIQ 17236 Generic[49], s[2], default[2]
    17264 | MIQ 17227 Generic[48], s[2], default[2]
    17286 | MIQ 17266 Schedule[52], s[2], default[2]
    17277 | MIQ 17245 Priority[50], s[2], default[2]
    17280 | MIQ 17254 Priority[51], s[2], default[2]
    17320 | MIQ 17298 Redhat::InfraManager::MetricsCollector[53], s[2],
    d..
    17329 | MIQ 17307 Redhat::InfraManager::MetricsCollector[54], s[2],
    d..
    [...]

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/10h
        startsin: 5.7
        title: pg_stat_activity view in postgres should show worker information
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_reporting():
    """
    Reporting (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_edit_request_task():
    """
    In this test we will try to edit a request using POST request.
    Note: Only Option field can be edited

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_osp_test_migration_plan_can_be_unscheduled():
    """
    OSP: Test migration plan can be unscheduled

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test migration plan can be unscheduled
    """
    pass


@pytest.mark.manual
@test_requirements.access
@pytest.mark.tier(1)
def test_switching_user_group_without_disconnecting():
    """
    Switching user"s group while user is online

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Open two private/anonymous windows in Firefox/Chrome/etc.
               Identify or create EvmRole-super_administrator level user admin
               Identify or create EvmRole-user level user testusr
               Identify or create EvmRole-user level group testGrp
        tags: rbac
        title: Switching user group without disconnecting
        testSteps:
            1. Sign up toa ppliance in browser1 as admin
            2. Sign up to appliance in browser2 as testusr
            3. Browser2: Navigate to Settings > About
            4.
            5. //About
            6. Browser1: Navigate to Settings > Configuration > Access Control
            7. Locate and select testusr
            8. Locate and select Configuration
            9. Select Edit
            10. Change group to EvmGroup-security
            11. Save user
            12. Browser2: Navigate to Settings > About
            13.
            14.
            15. Browser1: Navigate to Settings > Configuration > Access Control
            16. Locate and select testusr
            17. Locate and select Configuration
            18. Select Edit
            19. Change group to EvmGroup-user
            20. Save user
            21. Browser2: Navigate to Settings > About
            22.
            23.
            24. Browser1: Navigate to Settings > Configuration > Access Control
            25. Locate and select testusr
            26. Locate and select Configuration
            27. Select Edit
            28. Change group to testGrp
            29. Save user
            30. Browser2: Navigate to Settings > About
            31.
            32.
            33. Sign out both users
        expectedResults:
            1.
            2.
            3. Verify that user was not disconnected.
            4. Verify that testusr"s group is EvmGroup-user
            5. Verify that testusr"s role is EvmRole-user
            6.
            7.
            8.
            9. Verify you"ve been redirected to Editing User
            10.
            11.
            12. Verify that user was not disconnected.
            13. Verify that testusr"s group is EvmGroup-security
            14. Verify that testusr"s role is EvmRole-security
            15.
            16.
            17.
            18. Verify you"ve been redirected to Editing User
            19.
            20.
            21. Verify that user was not disconnected.
            22. Verify that testusr"s group is EvmGroup-user
            23. Verify that testusr"s role is EvmRole-user
            24.
            25.
            26.
            27. Verify you"ve been redirected to Editing User
            28.
            29.
            30. Verify that user was not disconnected.
            31. Verify that testusr"s group is testGrp
            32. Verify that testusr"s role is EvmRole-user
            33.
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_data_collector():
    """
    C & U Data Collector (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_test_multiple_sources_to_single_target_mapping_for_clusters_ds_network():
    """
    OSP: Test multiple sources to single target mapping (For Clusters, DS,
    Network)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test multiple sources to single target mapping (For Clusters, DS, Network)
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_volume_in_use_delete_openstack():
    """
    Requires:
    RHCF3-21779 - test_storage_volume_attach[openstack]
    Steps to test:
    1. Check after attached status of volume in-used or not
    2. Now try to delete volume from Detail page
    3. check for flash message " Cloud Volume "Volume_name" cannot be
    removed because it is attached to one or more Instances "
    4. Navigate on All page
    5. try to delete volume from All page
    6. check for flash message " Cloud Volume "Volume_name" cannot be
    removed because it is attached to one or more Instances "

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
def test_ec2_add_delete_add_provider():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1h
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_with_rhel_7x():
    """
    OSP: vmware67-Test VM migration with RHEL 7.x

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration with RHEL 7.x
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_credentials_change_password_trailing_whitespace():
    """
    Password with trailing whitespace

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_credentials_login_password_with_special_characters():
    """
    Alphanumeric password with special characters

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_api_edit_user_no_groups():
    """
    Verify that the CFME REST API does not allow you to edit a user and
    remove it from all assigned groups

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
        tags: rbac
        testSteps:
            1. Create a user and assign it to one or more groups
            2. Using the REST API, edit the user and attempt to assign it to no groups
        expectedResults:
            1. PASS
            2. FAIL
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_object_store_container_edit_tag_openstack():
    """
    Requirs:
    OpenstackProvider
    1) Add Object Store Container
    2) go to summery pages
    2) add tag : [Policy > Edit Tags]
    3) Verify the tag is assigned
    4) remove tag: [Policy > Edit Tags]
    5) Verify the tag is removed

    Polarion:
        assignee: mmojzis
        caseimportance: medium
        casecomponent: Cloud
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
def test_storage_ebs_volume_detach():
    """
    Requires:
    test_storage_ebs_volume_attach
    Steps to test:
    1. Go to Storage -> Block Storage -> Volumes
    2. Select volume from test_storage_ebs_volume_attach
    3. Configuration -> Detach this Cloud Volume
    4. Select instance from test_storage_ebs_volume_attach and Save
    5. Check whether volume was detached from that instance

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/6h
        casecomponent: Cloud
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_osp_test_associated_tags_before_and_after_migration_department_accounting_kind():
    """
    OSP: Test associated tags before and after migration
    (Department:Accounting kind)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test associated tags before and after migration
               (Department:Accounting kind)
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_stack():
    """
    Stack CREATE
    Stack DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_heat_stacks_in_non_admin_tenants_shall_also_be_collected():
    """
    Bugzilla:
        1290005

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Heat stacks in non-admin tenants shall also be  collected
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_web_services():
    """
    Web Services (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_vm_vsphere65():
    """
    Requires:
    C&U enabled Vsphere-65 appliance.
    Steps:
    1. Navigate to Datastores [Compute > infrastructure>VMs]
    2. Select any available VM (cu24x7)
    3. Go for utilization graphs [Monitoring > Utilization]
    4. Check data point on graphs ["CPU", "VM CPU state", "Memory", "Disk
    I/O", "N/w I/O"] using drilling operation on the data points.
    5.  check "chart" and "timeline" options working properly or not.

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_vm_vsphere6():
    """
    test_crosshair_op_vm[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_rightsize_memory_values_correct_vsphere6():
    """
    Right-size memory values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_rightsize_memory_values_correct_rhv41():
    """
    Right-size memory values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_saved_chargeback_report():
    """
    Verify that saved Chargeback reports are saved in the "Saved
    Chargeback Reports" folder on the Cloud Intelligence->Chargeback->
    Report page.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_test_create_migration_plan_create_and_read():
    """
    OSP: Test create migration plan - Create and Read

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test create migration plan - Create and Read
    """
    pass


@pytest.mark.manual
def test_osp_test_warnings_after_bad_failed_imports():
    """
    OSP: Test warnings after bad/failed imports

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test warnings after bad/failed imports
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_object_store_object_edit_tag_openstack():
    """
    Requirs:
    OpenstackProvider
    1) Navigate to Object Store Object [Storage > Object Storage > Object
    Store Objects]
    2) go to summery pages of any object
    2) add tag : [Policy > Edit Tags]
    3) Verify the tag is assigned
    4) remove tag: [Policy > Edit Tags]
    5) Verify the tag is removed

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_utilization_cluster():
    """
    Verify гutilication data from cluster

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 1/8h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_ec2_deploy_instance_with_ssh_addition_template():
    """
    Requirement: EC2 provider
    1) Provision an instance
    2) Select Choose Automatically in Environment -> Placement
    3) Select SSH key addition template in Customize -> Customize Template
    4) Instance should be provisioned without any errors

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_add_cloud_key_pair():
    """
    Add Cloud key pair
    Add Ec2 provider, Clouds - Key pair, Give any name , select provider.
    Click on Add .

    Polarion:
        assignee: mmojzis
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: Add Cloud Key pair
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_with_multiple_nics_with_single_ip_ipv6_to_first_nic_and_ipv4_to_():
    """
    OSP: vmware65-Test VM with multiple NICs with single IP (IPv6 to first
    NIC and IPv4 to second)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM with multiple NICs with single IP
               (IPv6 to first NIC and IPv4 to second)
    """
    pass


@pytest.mark.manual
@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_cluster():
    """
    Verify bottleneck events from cluster

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_verify_purging_of_old_records():
    """
    Verify that DriftState, MiqReportResult, EventStream, PolicyEvent,
    VmdbMetric, Metric, and Container-related records are purged
    regularly.
    Bug 1348625 - We might not be purging all tables that we should be

    Bugzilla:
        1348625

    [----] I, [2017-05-19T07:48:23.994536 #63471:985134]  INFO -- :
    MIQ(DriftState.purge_by_date) Purging Drift states older than
    [2016-11-20 11:48:20 UTC]...Complete - Deleted 0 records"
    [----] I, [2017-09-21T06:09:57.911327 #1775:a53138]  INFO -- :
    MIQ(MiqReportResult.atStartup) Purging adhoc report results...
    complete
    [----] I, [2017-09-21T06:15:31.118400 #2181:a53138]  INFO -- :
    MIQ(EventStream.purge) Purging all events older than [2017-03-25
    10:15:27 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T06:15:31.284846 #2181:a53138]  INFO -- :
    MIQ(PolicyEvent.purge_by_date) Purging Policy events older than
    [2017-03-25 10:15:31 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T06:50:25.643198 #2116:a53138]  INFO -- :
    MIQ(VmdbMetric.purge_by_date) Purging hourly metrics older than
    [2017-03-25 10:50:19 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T06:50:25.674445 #2116:a53138]  INFO -- :
    MIQ(VmdbMetric.purge_by_date) Purging daily metrics older than
    [2017-03-25 10:50:19 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-21T11:04:18.496532 #32143:a53138]  INFO -- :
    MIQ(Metric::Purging.purge) Purging all realtime metrics older than
    [2017-09-21 11:04:13 UTC]...Complete - Deleted 135 records and 0
    associated tag values - Timings: {:purge_metrics=>0.23389387130737305,
    :total_time=>0.23413729667663574}
    [----] I, [2017-09-27T15:37:42.206807 #6336:39d140]  INFO -- :
    MIQ(Container.purge_by_date) Purging Containers older than [2017-03-31
    19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.264940 #6326:39d140]  INFO -- :
    MIQ(ContainerGroup.purge_by_date) Purging Container groups older than
    [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.281474 #6336:39d140]  INFO -- :
    MIQ(ContainerImage.purge_by_date) Purging Container images older than
    [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.340960 #6336:39d140]  INFO -- :
    MIQ(ContainerDefinition.purge_by_date) Purging Container definitions
    older than [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records
    [----] I, [2017-09-27T15:37:42.392486 #6326:39d140]  INFO -- :
    MIQ(ContainerProject.purge_by_date) Purging Container projects older
    than [2017-03-31 19:37:38 UTC]...Complete - Deleted 0 records

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        initialEstimate: 1/4h
        startsin: 5.8
        title: Verify purging of old records
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_prov_from_service_ansible_tower_310():
    """
    1) Navigate to Configuration -> Configuration management -> Ansible
    Tower job templates.
    - click on job template -> Configuration -> Create service dialog from
    this job template -> give it name
    2) Create new catalog Item
    - Catalog Item type: AnsibleTower
    - name your catalog item
    - Display in catalog: checked
    - catalog: pick your catalog
    - Dialog: Tower_dialog
    - Provider: Ansible Tower .....
    3) Order service

    Polarion:
        assignee: nachandr
        casecomponent: Provisioning
        initialEstimate: 1h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_nor_cpu_vsphere6():
    """
    Test Normal Operating Range for CPU usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays values for CPU and CPU Usage
    max, high, average, and low, if at least one days" worth of metrics
    have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_nor_cpu_rhv41():
    """
    Normal Operating Ranges for CPU display correctly for RHV 4.1 VM.
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    RHV 4.1 provider
    Normal Operating Ranges widget displays values for CPU and CPU Usage
    max, high, average, and low, if at least one days" worth of metrics
    have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_nor_cpu_vsphere55():
    """
    Test Normal Operating Range for CPU usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 5.5 provider
    Normal Operating Ranges widget displays values for CPU and CPU Usage
    max, high, average, and low, if at least one days" worth of metrics
    have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
@pytest.mark.tier(2)
def test_retire_infra_vms_notification_folder():
    """
    test the retire funtion of vm on infra providers, select at least two
    vms and press retirement date button from vms main page and specify
    retirement warning period (1week, 2weeks, 1 months).

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_from_iscsi_storage_in_vmware_osp():
    """
    OSP: vmware65-Test VM migration from iSCSI Storage in VMware to NFS on
    OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration from iSCSI Storage in VMware OSP
    """
    pass


@pytest.mark.manual
def test_osp_test_retry_plan():
    """
    OSP: Test retry plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test retry plan
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_volume_detach_openstack():
    """
    Requires:
    test_storage_volume_attach[openstack]
    Steps to test:
    1. Go to Storage -> Block Storage -> Volumes
    2. Select volume from test_storage_openstack_volume_attach
    3. Configuration -> Detach this Cloud Volume from an instance
    4. Select instance from test_storage_openstack_volume_attach and Save
    5. Check whether volume was detached from that instance

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
@pytest.mark.tier(2)
def test_verify_that_users_can_access_help_documentation():
    """
    Verify that admin and user"s with access to Documentation can view the
    PDF documents

    Bugzilla:
        1563241

    Polarion:
        assignee: apagac
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
        title: Verify that users can access Help Documentation
        testSteps:
            1. Login as admin
            2. Verify that admin can access Help->Documentation and view
               the supporting documents
            3. Create a user with product feature Help->Documentation enabled
            4. Verify that admin can access Help->Documentation and view
               the supporting documents
        expectedResults:
            1. Login successful
            2. Help documents are visible
            3. User created
            4. Help document are visible
    """
    pass


@pytest.mark.manual
def test_osp_test_user_can_download_post_migration_ansible_playbook_log():
    """
    OSP: Test user can download post migration ansible playbook log

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test user can download post migration ansible playbook log
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_requests_in_ui_and_api():
    """
    Bugzilla:
        1608554

    1. Login with user with Services > My Services > Requests > Operate
    enabled
    2. View Services > Requests
    3. Query API on service_requests

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        tags: rbac
        title: Test requests in UI and API
    """
    pass


@pytest.mark.manual
def test_add_ec2_provider_with_instance_without_name():
    """
    1) Add an ec2 provider with instance without name
    2) Wait for refresh
    3) Refresh should complete without errors

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(3)
def test_chargeback_report_compute_provider():
    """
    Assign compute rates to provider;Generate chargeback report and verify
    that rates are applied to selected providers only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(3)
def test_chargeback_report_storage_tenants():
    """
    Assign storage rates to tenants;Generate chargeback report and verify
    that rates are applied to the tenant.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(3)
def test_chargeback_report_compute_tenants():
    """
    Assign compute rates to tenants;Generate chargeback report and verify
    that rates are applied to the tenant.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_report_storage_tagged_datastore():
    """
    Assign storage rates to tagged datastore;Generate chargeback report
    and verify that rates are applied to selected datastores only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_report_storage_enterprise():
    """
    Assign storage rates to Enterprise;Generate chargeback report and
    verify that rates are applied to Enterprise

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_report_compute_cluster():
    """
    Assign compute rates to cluster;Generate chargeback report and verify
    that rates are applied to selected clusters only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_report_compute_enterprise():
    """
    Assign compute rates to Enterprise;Generate chargeback report and
    verify that rates are applied to Enterprise

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(3)
def test_chargeback_report_compute_tagged_vm():
    """
    Assign compute rates to tagged Vms;Generate chargeback report and
    verify that rates are applied to tagged VMs only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(3)
def test_chargeback_report_storage_datastore():
    """
    Assign storage rates to datastore;Generate chargeback report and
    verify that rates are applied to selected datastores only

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
@pytest.mark.tier(2)
def test_authorized_users_can_login():
    """
    Verify that authorized users can login successfully with a valid
    password

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_remove_objects_ansible_tower_310():
    """
    1) Add Configuration manager
    2) Perform refresh and wait until it is successfully refreshed
    3) Remove provider
    4) Click through accordion and double check that no objects (e.g.
    tower job templates) were left in the UI

    Polarion:
        assignee: nachandr
        caseimportance: medium
        casecomponent: Ansible
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_set_ownership_back_to_default():
    """
    Bugzilla:
        1483512

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        title: Set Ownership back to default
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
def test_can_only_select_this_regions_zones_when_changing_server_zone():
    """
    Bug 1470283 - zones of sub region show up as zones appliances of a
    central region can move to

    Bugzilla:
        1470283

    Configure 1 appliance for use as a reporting db server, with region
    99. Create zones zone-99-a and zone-99-b.
    Configure a 2nd appliance as a remote appliance, with region 0. Create
    zones zone-0-a and zone-0-b.
    In the web UI of the 1st appliance, change the zone of the appliance.
    Verify that only the zones for this appliance"s region (i.e.,
    zone-99-a and zone-99-b) appear in the drop-down list.
    1.) Set up first appliance:
    a.) Request appliance that isn"t pre-configured.
    b.) ssh to appliance and run appliance_console.
    c.) Choose:
    > Configure Database
    > Create key
    > Create Internal Database
    Should this appliance run as a standalone database server?    ? (Y/N):
    |N|
    Enter the database region number: 99
    Enter the database password on 127.0.0.1: smartvm
    d.) Log in to the web UI and enable only the following Server Roles:
    Reporting
    Scheduler
    User Interface
    Web Services
    e.) Create two more zones: tpapaioa-99-a and tpapaioa-99-b
    2.) set up second appliance:
    a.) request appliance that is pre-configured.
    b.) Log in to the web UI and enable replication:
    Administrator > Configuration > Settings > Region 0 > Replication >
    Type: Remote > Save
    3.) on the first appliance:
    a.) set up replication for the second appliance:
    Administrator > Configuration > Settings > Region 99 > Replication >
    Type: Global > Add Subscription >
    Database    vmdb_production
    Host        <ip address of 2nd appliance>
    Username    root
    Password    smartvm
    Port        5432
    > Accept > Save
    4.) on the second appliance, create two more zones: tpapaioa-0-a and
    tpapaioa-0-b.
    5.) on the first appliance, click on the appliance"s Zone drop-down
    menu, and verify that only tpapaioa-99-a and tpapaioa-99-b are
    visible:
    Administrator > Configuration > Server > Zone

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Can only select this region's zones when changing server zone
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_with_windows_7():
    """
    OSP: vmware65-Test VM migration with Windows 7

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration with Windows 7
    """
    pass


@pytest.mark.manual('manualonly')
def test_ec2_flavor_list_up_to_date():
    """
    Requirement: EC2 Provider
    1) Go to Compute -> Cloud -> Instances
    2) Try to provision an HVM instance
    3) Go to Properties and compare hvm instance types with HVM instance
    types in AWS console.
    4) AWS console instance types list should be equal to instance types
    in CFME
    5) Try to provision an paravirtual instance
    6) Go to Properties and compare paravirtual instance types with
    paravirtual instance types in AWS console.
    7) AWS console instance types list should be equal to instance types
    in CFME

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/3h
        casecomponent: Cloud
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_with_windows_10():
    """
    OSP: vmware67-Test VM migration with Windows 10

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration with Windows 10
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_candu_graphs_vm_compare_cluster_vsphere6():
    """
    test_candu_graphs_vm_compare_cluster[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_candu_graphs_vm_compare_cluster_vsphere65():
    """
    test_candu_graphs_vm_compare_cluster[vsphere65]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_crosshair_op_instance_gce():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_crosshair_op_instance_azure():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_crosshair_op_instance_ec2():
    """
    Verify that the following cross-hair operations can be performed on
    each of the C&U graphs for an instance:
    1.Chart
    1.1 Hourly for this day and then back to daily
    2.Timeline
    2.1 Daily events on this VM
    2.2 Hourly events for this VM

    Polarion:
        assignee: mshriver
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_osp_test_edit_migration_plan():
    """
    OSP: Test edit migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test edit migration plan
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_candu_graphs_cluster_hourly_vsphere55():
    """
    test_candu_graphs_cluster_hourly[vsphere55]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_resource_allocation_cpu_allocated():
    """
    Verify CPU allocation in a Chargeback report based on resource
    allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_resource_allocation_memory_allocated():
    """
    Verify memory allocation in a Chargeback report based on resource
    allocation.C&U data is not considered for these reports.

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_resource_allocation_storage_allocated():
    """
    Verify storage allocation in a Chargeback report based on resource
    allocation. C&U data is not considered for these reports.

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_optimize_memory_usage_by_making_object_in_hash():
    """
    The object in the hash reference should be as small as possible,
    so we don"t need to store that many data in memory.

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1h
        title: Optimize memory usage by making object in hash
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_volume():
    """
    #AWS naming is EBS
    Volume CREATE
    Volume UPDATE
    Volume DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_from_nfs_storage_in_vmware_to_iscsi_on_osp():
    """
    OSP: vmware67-Test VM migration from NFS Storage in VMware to iSCSI on
    OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration from NFS Storage in VMware to iSCSI on OSP
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_view_quotas_without_manage_quota_permisson():
    """
    Bugzilla:
        1535556

    1. disable "manage quota" from the role of a user
    2. try to view quotas as that user
    copy the EVMRole-tenant_quota_administrator role, disable Settings ->
    Configuration -> Access Control -> Tenants -> Modify -> Manage Quotas
    and still view quotas when the "Manage Quotas" button was no longer
    available.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        tags: rbac
        title: Test view quotas without manage quota permisson
    """
    pass


@pytest.mark.manual
def test_ec2_proxy():
    """
    1) Go to Configuration -> Advanced Settings
    2) Find:
    :http_proxy:
    :ec2:
    :host:
    :password:
    :port:
    :user:
    and fill in squid proxy credentials
    3) Add an ec2 provider
    4) Check whether traffic goes through squid proxy
    5) Check whether ec2 provider was refreshed successfully

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_datastore_vsphere65():
    """
    Requires:
    C&U enabled Vsphere-65 appliance.
    Steps:
    1. Navigate to Datastores [Compute > infrastructure>Datastores]
    2. Select any available datastore
    3. Go for utilization graphs [Monitoring > Utilization]
    4. Check data point on graphs ["Used Disk Space", "Hosts", "VMs"]
    using drilling operation on the data points.
    5.  check "chart" and "display" option working properly or not.

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_bundle_stack_deployment():
    """
    bundle stack provisioning for entry point catalog items

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_provider_refresh_via_api():
    """
    Bugzilla:
        1602413

    1. set up a new user with a new group based on vm_user plus api access
    and refresh access to cloud and infrastructure providers
    2. issue a refresh using the classic ui with that user
    3. issue a refresh of the same provider using the api

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        tags: rbac
        title: Test provider refresh via API
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_tenant_parent_name_rest():
    """
    When you change the main parent tenant"s name that change is not
    reflected in api calls

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_utilization_host():
    """
    Verify utilication data from host

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 1/8h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
@pytest.mark.tier(2)
def test_credentials_login_password_blank():
    """
    No password

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
def test_osp_test_vm_owner_before_and_after_migration_remains_same():
    """
    OSP: Test VM owner before and after migration remains same

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test VM owner before and after migration remains same
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_nor_memory_values_correct_vsphere6():
    """
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays correct values for Memory and
    Memory Usage max, high, average, and low, if at least one days" worth
    of metrics have been captured:
    The Average reflects the most common value obtained during the past 30
    days" worth of captured metrics.
    The High and Low reflect the range of values obtained ~85% of the time
    within the past 30 days.
    The Max reflects the maximum value obtained within the past 30 days.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_nor_memory_values_correct_rhv41():
    """
    NOR memory values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_gap_collection_vsphere6():
    """
    Draft

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
def test_osp_test_migrating_a_vm_which_has_encrypted_disk():
    """
    OSP: Test migrating a VM which has encrypted disk

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test migrating a VM which has encrypted disk
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_group_by_tag_azone_azure():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_group_by_tag_azone_gce():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(3)
def test_distributed_zone_create_new():
    """
    Create new zone in local region

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_with_rhel_74_5():
    """
    OSP: vmware60-Test VM migration with RHEL 7.4/5

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration with RHEL 7.4/5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_verify_smart_mgmt_orchest_template():
    """
    Verify Smart Management section in Orchestration template summary
    page.

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/4h
        startsin: 5.5
        testtype: structural
    """
    pass


@pytest.mark.manual
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
        title: OSP: vmware60-Test VM with multiple Disks
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_notification_window_events_show_in_timestamp_order():
    """
    Bug 1469534 - The notification events are out of order

    Bugzilla:
        1469534

    If multiple event notifications are created near-simultaneously (e.g.,
    several VM"s are provisioned), then clicking on the bell icon in the
    top right of the web UI displays the event notifications in timestamp
    order.

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: Notification window events show in timestamp order
    """
    pass


@pytest.mark.manual
def test_osp_test_migration_plan_can_be_scheduled_to_run_at_later_date_time():
    """
    OSP: Test migration plan can be scheduled to run at later date/time

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test migration plan can be scheduled to run at later date/time
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_rightsize_cpu_vsphere55():
    """
    Test Right size recommendation for cpu

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_rightsize_cpu_vsphere6():
    """
    Test Right size recommendation for cpu

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_rightsize_cpu_rhv41():
    """
    For a RHV 4.1 provider with C & U metrics collection configured and
    running for >1 day, a VM that has been up and running for >1 day shows
    values in all cells of the tables displayed on the Right-Size
    Recommendations page:
    Compute > Infrastructure > Virtual Machines > click on VM name >
    Configuration > Right-Size Recommendations

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
@pytest.mark.tier(2)
def test_verify_orchestration_catalog_items_can_only_use_providers_that_are_visible_to_the_use():
    """
    When creating a new catalog item of type "Orchestration", the
    available providers should be restricted to providers that are visible
    to the user

    Polarion:
        assignee: apagac
        casecomponent: Control
        caseimportance: medium
        initialEstimate: 1/4h
        setup: On CFME appliance, add a Microsoft Azure provider with no restrictions
        title: Verify orchestration catalog items can only use providers
               that are visible to the user
        testSteps:
            1. As admin: Create an administrator group that restricts
               access to objects with a certain tag.
            2. As admin: Create a user that is assigned to the restricted group
            3. Restricted user: Verfiy that the Azure provider is not visible
            4. Create a new catalog item with type "Orchestration" and
               Orchestration Template of type azure
            5. When the provider option is visible, verify that any
               providers listed are visible providers
            6. As admin: Change the tag for the azure provider to match
               tags that are accessible by the restricted user
            7. As the restricted user: Verify that the cloud provider is now visible
            8. Attempt to create a new catalog item of type
               "Orchestration", Orchestration Template for azure and
               confirm that the azure provider is an available option
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_osp_test_osp_volumes_are_cleaned_up_if_migration_fails_to_create_instance():
    """
    V2V Test following BZs

    Bugzilla:
        1651352
        1653412

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/4h
        title: OSP: Test OSP Volumes are cleaned up if migration fails to create instance
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_consistent_capitalization_of_cpu_when_creating_compute_chargeback_rate():
    """
    Consistent capitalization of "CPU":
    1.) When adding a Compute Chargeback Rate, the "CPU" group should not
    change to "Cpu" when you click the "Add" button to add a second
    tier/row.
    2.) The "CPU Cores" group should not display as "Cpu Cores".

    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/15h
        title: Consistent capitalization of 'CPU' when creating compute chargeback rate
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_show_tag_info_for_playbook_services():
    """
    Bugzilla:
        1449020

    Polarion:
        assignee: sshveta
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        title: Show tag info for playbook services
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_coordinator_singleton():
    """
    C & U Coordinator (singleton role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_stack_parent():
    """
    This test is where you need to verify that the VM Instance created by
    an Orchestration Stack has, or can have, it"s parent relationship set.

    Polarion:
        assignee: sshveta
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/8h
        setup: This test is pretty straight forward.  Spin up a VM using and
               orchestration template.  Go to the instance details. Select Edit this
               Instance
        testSteps:
            1. Set Parent for VM Instance
        expectedResults:
            1. The possible parents are listed and can be saved
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_with_windows_2012_server():
    """
    OSP: vmware65-Test VM migration with Windows 2012 server

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration with Windows 2012 server
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_subnet():
    """
    Subnet CREATE
    Subnet UPDATE
    Subnet DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_usage_storage():
    """
    Validate cost for storage usage for a VM in a monthly chargeback
    report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_usage_disk():
    """
    Validate cost for disk io for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_allocation_cpu():
    """
    Validate cost for VM cpu allocation in a monthly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_allocation_storage():
    """
    Validate cost for VM storage allocation in a monthly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_usage_cpu():
    """
    Validate cost for CPU usage for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_allocation_memory():
    """
    Validate cost for VM memory allocation in a monthly report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_usage_memory():
    """
    Validate cost for memory usage for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_monthly_usage_network():
    """
    Validate cost for network io for a VM in a monthly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vm_tempate_ownership_nogroup():
    """
    test assigning no groups ownership for vm and templates
    Bugzilla:
        1330022
        1456681

    UPDATE: There was no movement on BZ 1456681 for a long time. If this
    BZ is not resolved, we don"t know how exactly the ownership should
    behave in certain situations and this testcase will always fail.
    Assigning no group ownership should work fine.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_with_multiple_disks():
    """
    OSP: vmware67-Test VM with multiple Disks

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM with multiple Disks
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_retire_ansible_stack():
    """
    Retire Ansible stack

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        setup: 1. Add Ansible Tower provider (name: tower) and perform refresh
               2. Navigate to Ansible Tower Job templates, click on configured job ->
               Configuration -> Create service dialog from this template (name it:
               first_job_template_dialog)
               3. Go to Services -> Catalog and create new catalog_tower
               4. Create new catalog item under your new catalog
               5. Catalog item parameters:
               Catalog Item Type: AnsibleTower
               Name: tower
               Display in catalog: checked
               Catalog: catalog_tower
               Dialog: first_job_template_dialog
               Provider: tower
               Ansible Tower Job Template: first_job_template
               6. Click on Add button and order this service
               7. Monitor that job has been executed correctly on Ansible Tower side
               and that in CFME is completed successfully
               8. Navigate to Compute -> Clouds -> Stacks
               9. Select first_job_template stack -> Lifecycle -> Retire selected
               stacks
        startsin: 5.5
        title: Retire Ansible stack
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_azone_group_by_tag_ec2():
    """
    test_azone_group_by_tag[ec2]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_osp_test_policy_to_prevent_source_vm_from_starting_if_migration_is_comaplete():
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
        title: OSP: Test policy to prevent source VM from starting if migration is comAplete
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_verify_that_when_modifying_rbac_roles_existing_enabled_disabled_product_features_dont():
    """
    When modifying RBAC Roles, all existing enabled/disabled product
    features should retain their state when modifying other product
    features.

    Polarion:
        assignee: apagac
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/4h
        tags: rbac
        title: Verify that when modifying RBAC Roles, existing
               enabled/disabled product features don't change state when
               modifying other features
        testSteps:
            1. Navigate to access control and create a new role with all
               product features enabled
            2. Edit the role, disable 1 or more product features and save the changes
            3. Create a new role with only one sub product feature enabled and save it
            4. Modify the previous role and enable an additional product
               feature. Save the modifications.
        expectedResults:
            1. New role created successfully
            2. Only the user modified feature(s) should be changes
            3. Only the single product feature should be enabled
            4. Only the specified product features should be enabled
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_check_all_availability_zones_for_amazon_provider():
    """
    Check if all availability zones can be selected while creating catalog
    item.

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Check all availability zones for amazon provider
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_with_mutliple_nics_with_single_ip_ipv6_to_first_nic_and_ipv4_to_():
    """
    vmware67-Test VM with mutliple NICs with single IP (IPv6 to first NIC
    and IPv4 to second

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM with mutliple NICs with single IP
               (IPv6 to first NIC and IPv4 to second)
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_load_balancer():
    """
    #AWS naming is ELB
    Apply Security group
    Floating IP CREATE
    Floating IP UPDATE
    Floating IP DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_change_zone():
    """
    Add Ansible Tower in multi appliance, add it to appliance with UI. Try
    to change to zone where worker is enabled.

    Bugzilla:
        1353015

    Polarion:
        assignee: nachandr
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_verify_that_a_user_with_a_custom_tag_can_view_vms_with_the_same_tag():
    """
    When a user is assigned a custom tag restricting visible items, verify
    that the user can only see VMs with the same tag.
    See: https://access.redhat.com/articles/421423 and
    https://cloudformsblog.redhat.com/2016/10/13/using-tags-for-access-
    control

    Polarion:
        assignee: apagac
        casecomponent: Provisioning
        initialEstimate: 1/3h
        setup: Add a provider with two VMs available for tagging
        tags: rbac
        title: Verify that a user with a custom tag can view VMs with the same tag
        testSteps:
            1. Create a custom Category and tag
            2. Tag a VM with the custom tag and tag another VM with a different tag
            3. Create a new group with the custom tag
            4. Create a new user and assign it to the new group
            5. Login as the new user and attempt to view the VM with the custom tag
        expectedResults:
            1. Category & tag created successfully
            2. VMs tagged successfully
            3. Group created successfully
            4. User created successfully
            5. User can see the VM with the custom tag and not the VM with a different tag
    """
    pass


@pytest.mark.manual
def test_storage_ebs_snapshot_delete():
    """
    Requires: test_storage_ebs_snapshot_create
    1) Delete previously created EBS snapshot from volume
    2) Check whether snapshot is not displayed anymore

    Polarion:
        assignee: mmojzis
        caseimportance: medium
        casecomponent: Cloud
        initialEstimate: 1/15h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_candu_graphs_datastore_vsphere6():
    """
    test_candu_graphs_datastore[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_from_iscsi_storage_in_vmware_to_nfs_on_osp():
    """
    OSP: vmware67-Test VM migration from iSCSI Storage in VMware to NFS on
    OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration from iSCSI Storage in VMware to NFS on OSP
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_with_multiple_disks():
    """
    OSP: vmware65-Test VM with multiple Disks

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM with multiple Disks
    """
    pass


@pytest.mark.manual
def test_ec2_security_group_record_values():
    """
    Bugzilla:
        1540283

    Polarion:
        assignee: mmojzis
        caseimportance: medium
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_from_iscsi_storage_vmware_to_osp():
    """
    OSP: vmware60-Test VM migration from iSCSI Storage VMware to iSCSI in
    OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration from iSCSI Storage VMware to OSP
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_smartstate_analysis():
    """
    SmartState Analysis (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_osp_vmware_60_test_vm_name_with_punycode_characters():
    """
    OSP: vmware 60- Test VM name with Punycode characters

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware 60- Test VM name with Punycode characters
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_multiple_stack_deployment():
    """
    Create bundle of stack and provision

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Multiple Stack deployment
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_volume_attach_openstack():
    """
    Requires:
    An Openstack Cloud Provider
    Step to test:
    1. Create an Openstack instance
    2 . Go to Storage -> Block Storage -> Volumes
    3. Create an Openstack Volume
    4. Select created volume
    5. Configuration -> Attach this Cloud Volume
    Fill in form:
    Created instance
    /dev/sdf
    6. Check whether volume was attached to that instance

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_field_zone_name_whitespace():
    """
    When creating a new zone, the name can have whitespace, including
    leading and trailing characters. After saving, any leading or trailing
    whitespace is not displayed in the web UI.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_create_duplicate():
    """
    Create Zone with name that is already in use.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.genealogy
@pytest.mark.tier(2)
def test_edit_vm():
    """
    Edit infra vm and cloud instance

    Bugzilla:
        1399141
        1399144

    When editing cloud instance, genealogy should be present on the edit
    page.
    When you have two providers - one infra and one cloud - added, there
    should be no cloud vms displayed when setting genealogy for infra vm
    and vice-versa.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_from_nfs_storage_in_vmware_to_osp():
    """
    OSP: vmware60-Test VM migration from NFS Storage in VMware to iSCSI on
    OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration from NFS Storage in VMware to OSP
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_with_windows_2016_server():
    """
    OSP: vmware60-Test VM migration with Windows 2016 server

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration with Windows 2016 server
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_rightsize_cpu_values_correct_rhv41():
    """
    For a RHV 4.1 provider with C & U metrics collection configured and
    running for >1 day, a VM that has been up and running for >1 day shows
    correct recommended CPU values on the Right-Size Recommendations page:
    Compute > Infrastructure > Virtual Machines > click on VM name >
    Configuration > Right-Size Recommendations
    The correct Max, High, Average, and Low CPU and CPU Usage values in
    the Normal Operating Ranges table should be determined by the maximum,
    ~85th percentile, ~50th percentile, and ~15th percentile CPU (MHz) and
    CPU Usage (%) realtime metric values from the past 30 days for this
    VM.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_rightsize_cpu_values_correct_vsphere6():
    """
    Right-size recommended cpu values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_field_zone_name_long():
    """
    When creating a new zone, the name can be up to 50 characters long,
    and displays correctly after saving.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
@pytest.mark.tier(2)
def test_retire_infra_vms_date_folder():
    """
    test the retire funtion of vm on infra providers, at least two vm, set
    retirement date button from vms page(without notification)

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_osp_vmware60_test_vm_migration_with_windows_10():
    """
    OSP: vmware60-Test VM migration with Windows 10

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware60-Test VM migration with Windows 10
    """
    pass


@pytest.mark.manual
@test_requirements.replication
def test_distributed_zone_in_different_networks():
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        initialEstimate: 1h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_verify_that_errored_out_queue_messages_are_removed():
    """
    Verify that errored-out queue messages are removed.
    Bug 1460263 - shutdown_and_exit messages get marked as error and never
    removed from miq_queue table

    Bugzilla:
        1460263

    # appliance_console
    -> Stop EVM Server Processes
    -> Start EVM Server Processes
    # cd /var/www/miq/vmdb/
    # bin/rails c
    irb(main):001:0> MiqQueue.where(:state => "error")

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/15h
        title: Verify that errored-out queue messages are removed
    """
    pass


@pytest.mark.manual
@test_requirements.satellite
def test_satellite_credential_validation_times_out_with_error_message():
    """
    Bug 1564601 - Satellite credential validation times out with no error
    message

    Bugzilla:
        1564601

    When adding a new Satellite configuration provider, if the URL cannot
    be accessed because of a firewall dropping packets, then credential
    validation should time out after 2 minutes with a flash message.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/6h
        title: Satellite credential validation times out with error message
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_session_timeout_works_fine_for_external_auth():
    """
    As admin change the session timeout in cfme webui.
    Login as ldap user and verify session times out after the specified
    timeout value.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
        title: Verify session timeout works fine for external auth.
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_button_groups_created_on_orchestration_type_heat_service_catalog_items_are_not_seen_o():
    """

    Bugzilla:
        1496190

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/4h
        title: Button groups created on orchestration type (heat) service
               catalog items are not seen on services
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_default_value_on_dropdown_inside_dialog():
    """

    Bugzilla:
        1516721

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        title: Test default value on Dropdown inside Dialog
    """
    pass


@pytest.mark.manual
def test_osp_test_imports_with_non_existing_vm_name_should_give_error():
    """
    OSP: Test imports with non-existing VM name (Should give error)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test imports with non-existing VM name (Should give error)
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_scheduler_singleton():
    """
    Scheduler (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_with_windows_2016_server():
    """
    OSP: vmware65-Test VM migration with Windows 2016 server

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration with Windows 2016 server
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_credentials_change_password_greater_than_16_chars():
    """
    Password > 16 char

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.bottleneck
@pytest.mark.tier(1)
def test_bottleneck_summary_graph():
    """
    test_bottleneck_summary_graph

    Polarion:
        assignee: nachandr
        casecomponent: Optimize
        initialEstimate: 1/4h
        testSteps:
            1. setup c&u for provider and wait for bottleneck events
        expectedResults:
            1. summary graph is present and clickeble
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_report_filter_owner():
    """
    Verify that chargeback reports can be generated by filtering on
    owners.Make sure to include the "owner" column in the report.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(3)
def test_chargeback_report_filter_tag():
    """
    Verify that chargeback reports can be generated by filtering on tags

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_storage_ebs_volume_attach():
    """
    Requires:
    An ec2 provider
    Step to test:
    1. Create an ec2 instance in region us-east-1
    2. Create an ebs volume in region us-east-1
    3. Go to Storage -> Block Storage -> Volumes
    4. Select created volume
    5. Configuration -> Attach this Cloud Volume
    Fill in form:
    Created instance
    /dev/sdf
    6. Check whether volume was attached to that instance

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_restricted_user_rbac_for_access_control():
    """
    Bugzilla:
        1311399

    Navigate to Configure ==> Configuration ==> Access Control.
    Create a new role with "VM & Template Access Restriction" as "Only
    User or Group Owned" or "Only User Owned".  Make sure all the module
    access is given in "Product Features (Editing)" i.e., Everything is
    checked.
    Create a new group with the above role.
    Create a new user with the above group.
    Login with the newly created user and navigate to Configure ==>
    Configuration ==> Access Control.
    Click on Users or Groups.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_with_really_long_name_upto_64_chars_worked_not_65_char():
    """
    OSP: vmware65-Test VM migration with really long name(Upto 64 chars
    worked, not 65 chars)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration with really long name(Upto
               64 chars worked, not 65 chars)
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
def test_vms_retirement_state_field_is_capitalized_correctly():
    """
    Bug 1518926 - Inconsistent capitalization for Retirement State field

    Bugzilla:
        1518926

    When a VM is retiring or retired, the VM should show a "Retirement
    State" field, not "Retirement state".

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/15h
        title: VM's Retirement State field is capitalized correctly
    """
    pass


@pytest.mark.manual
def test_osp_test_user_can_run_post_migration_ansible_playbook():
    """
    OSP: Test user can run post migration ansible playbook

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test user can run post migration ansible playbook
    """
    pass


@pytest.mark.manual
def test_osp_test_user_can_download_pre_migration_ansible_playbook_log():
    """
    OSP: Test user can download pre migration ansible playbook log

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test user can download pre migration ansible playbook log
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_disabled_vsphere65_opsui_ssui():
    """
    For all versions of CFME 5.7 onward, VNC console should be Disabled
    for vsphere65 in OPSUI and SSUI

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseposneg: negative
        initialEstimate: 1h
        startsin: 5.7
        testSteps:
            1. Select VMware Console Support to VNC in CFME and Try to
               Access VM Console in OPS UI
            2. Create a Service to provision VM on vSphere65, open SUI,
               provision service, select provisioned service, On details
               page, try to access VM Console
        expectedResults:
            1. VM Console button is disabled
            2. VM Console is disabled
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_from_ubuntu():
    """
    OSP: vmware67-Test VM migration from ubuntu

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration from ubuntu
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_field_zone_description_leading_whitespace():
    """
    Leading whitespace in description

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_chargeback_report_monthly():
    """
    Verify that 1)monthly chargeback reports can be generated and 2)that
    the report contains relevant data for the relevant period.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_duplicate_groups_when_setting_ownership_to_multiple_items():
    """
    Bugzilla:
        1589009

    1. Navigate to Infrastructure -> Provider -> Vmware
    2. select multiple vms and go to Configuration -> Set ownership
    3. Under group list, duplicate group names listed.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
        title: Test duplicate groups when setting ownership to multiple items
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(3)
def test_saved_chargeback_report_show_full_screen():
    """
    Verify that saved chargeback reports can be viewed

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_with_rhel_69():
    """
    OSP: vmware67-Test VM migration with RHEL 6.9

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration with RHEL 6.9
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_change_appliance_zone():
    """
    Move an appliance from one zone to another.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
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
        title: OSP: Test creating multiple mappings with same name
    """
    pass


@pytest.mark.manual
def test_osp_test_migrations_with_multi_zonal_setup():
    """
    OSP: Test migrations with multi-zonal setup

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test migrations with multi-zonal setup
    """
    pass


@pytest.mark.manual
def test_osp_test_migration_using_vddk_connection_type_for_vmware():
    """
    OSP: Test Migration using VDDK (Connection type for VMware)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test Migration using VDDK (Connection type for VMware)
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_cloud_key_pair_validation():
    """
    Cloud - Key pair - without filling data , click on add

    Polarion:
        assignee: mmojzis
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: Cloud Key pair validation
    """
    pass


@pytest.mark.manual
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
        title: OSP: Test mapping can be created with name including international chars
    """
    pass


@pytest.mark.manual
def test_cluster_and_project_availablity_in_source_and_target():
    """
    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: RHV
        title: Test cluster and project availablity in source and target
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_host_vsphere65():
    """
    Requires:
    C&U enabled Vsphere-65 appliance.
    Steps:
    1. Navigate to Hosts [Compute > infrastructure>Hosts]
    2. Select any available host
    3. Go for utilization graphs [Monitoring > Utilization]
    4. Check data point on graphs ["CPU", "VM CPU state", "Memory", "Disk
    I/O", "N/w I/O", VMs] using drilling operation on the data points.
    5.  check "chart", "timeline" and "display" option working properly or
    not.

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_host_vsphere6():
    """
    test_crosshair_op_host[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_invalid_user_login_fails():
    """
    Login with invalid user
    Authentication expected to fail, check audit.log and evm.log for
    correct log messages.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        title: Verify invalid user login fails
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_rightsize_memory_rhv41():
    """
    For a RHV 4.1 provider with C & U metrics collection configured and
    running for >1 day, a VM that has been up and running for >1 day shows
    values in all cells of the tables displayed on the Right-Size
    Recommendations page:
    Compute > Infrastructure > Virtual Machines > click on VM name >
    Configuration > Right-Size Recommendations

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_rightsize_memory_vsphere55():
    """
    Test Right size recommendation for memory

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_rightsize_memory_vsphere6():
    """
    Test Right size recommendation for memory

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_credentials_change_password_leading_whitespace():
    """
    Password with leading whitespace

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
@pytest.mark.tier(2)
def test_retire_cloud_vms_folder():
    """
    test the retire funtion of vm on cloud providers, at leat two vm,
    retire now button vms page

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_automation_request_task():
    """
    In this test we will try to edit a automation request using POST
    request.
    Note: Only Option field can be edited

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_service_chargeback_vm_poweredoff():
    """
    Validate Chargeback costs for a service with a VM that has been
    powered off

    Polarion:
        assignee: nachandr
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_osp_test_scheduled_retirement_remains_same_in_migrated_vm():
    """
    OSP: Test scheduled retirement remains same in migrated VM

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test scheduled retirement remains same in migrated VM
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_with_rhel_69():
    """
    OSP: vmware65-Test VM migration with RHEL 6.9

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration with RHEL 6.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_active_tasks_get_timed_out_when_they_run_too_long():
    """
    active tasks get timed out when they run too long
    Bug 1397600 - After killing reporting worker, report status still says
    Running

    Bugzilla:
        1397600

    ****
    1.) Set task timeout check frequency and timeout values:
    :task_timeout_check_frequency: 600
    :active_task_timeout: 10.minutes
    2.) Queue a bunch of reports.
    3.) Kill the MiqReportingWorker pid(s).
    4.) Repeat #2 and #3 a couple times, until one of the reports gets
    stuck with a Running status.
    5.) After ~10 minutes, see entries like the following in evm.log, and
    verify that the reports show a status of Error in the web UI.
    [----] I, [2017-06-12T16:05:14.491076 #18861:3bd134]  INFO -- :
    MIQ(MiqTask#update_status) Task: [213] [Finished] [Error] [Task [213]
    timed out - not active for more than 600 seconds]
    ****

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.7
        title: active tasks get timed out when they run too long
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_ordering_service_by_non_admin_user():
    """
    Bugzilla:
        1546944

    1. Go to Access Control, Create a role named "service_role" with below
    roles should be enabled i.e. Compute and Services.
    2. Create a user i.e. "service_user" based on this "service_role"
    3. Login with service_user and while ordering the catalog, it is
    throwing 403 Forbidden exception.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        title: Test ordering service by non-admin user
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_gap_collection_hourly_graph_vsphere6():
    """
    Draft

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_provider_inventory_singleton():
    """
    Provider Inventory (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_deployment_multiple_instances():
    """
    Deployment of mutiple instances in same stack

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_provider_operations():
    """
    Provider Operations (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_test_archive_completed_migration_plan():
    """
    OSP: Test Archive completed migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test Archive completed migration plan
    """
    pass


@pytest.mark.manual
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
        title: OSP: Test migration logs from conversion host can be
               retrieved from miq appliance
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_evmgroup_self_service_user_can_access_the_self_service_ui():
    """
    Verify that a user in the assigned to the EVMRole-self_service and
    EVMRole-self_service can login to the SSUI

    Polarion:
        assignee: apagac
        casecomponent: SelfServiceUI
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.8
        title: EVMGroup-self_service user can access the Self Service UI
        testSteps:
            1. Create a user assigned to the default role of EVMRole-self_service
            2. Login to the SSUI with the user
        expectedResults:
            1. User created successfully
            2. SSUI access granted
    """
    pass


@pytest.mark.manual
def test_osp_test_user_can_run_pre_migration_ansible_playbook():
    """
    OSP: Test user can run pre migration ansible playbook

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test user can run pre migration ansible playbook
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tenant_template_visibility():
    """
    Create group with role "user owned only"
    As admin navigate to templates and set ownership for user
    Log in as user, check template is visible for user(only this template)

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartportnegative_endportnegative():
    """
    Should fail to open console

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_ssui_rhel():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
            7. Repeat previous 2 steps in Firefox version latest, latest-1, latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
            7. All should behave the same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_ie11_vsphere6_win7():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_edge_ssui_win10():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere55_win7():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartport5955_endportblank():
    """
    Should open connections for VNC port starting 5955 and keep opening
    until ports exhausted.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_vsphere6_fedora28():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_ssui_fedora():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_vsphere55_fedora28():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_vsphere55_fedora28():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_html5_console_inaddproviderhoststartvncportpresent():
    """
    Bugzilla:
        1514594

    Check to see if the Add provider screen has the Host VNC Start Port
    and Host VNC End port.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_ssui_rhel():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere6_win2012():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere6_win10():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartportblank_endport5901():
    """
    Should open connections for VNC port starting 5900 and end at 5901

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere6_rhel6x():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_vsphere55_fedora26():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_vsphere6_fedora26():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
def test_html5_console_edge_rhevm41_win10_vnc():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
def test_html5_console_firefox_rhevm41_fedora28_vnc():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere55_rhel7x():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testtype: integration
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere55_win10():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
def test_html5_console_firefox_rhevm41_fedora28_spice():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_ie11_vsphere55_win2012():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_vsphere6_fedora26():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for Firefox Version Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vsphere6_ssui():
    """
    Bugzilla:
        1597393

    VMware VNC Remote
    Console does not work in SSUI with following error:
    There was an error opening the console. undefined
    Steps to Reproduce:
    1.Add VMware 6.0 or less provider to CFME
    2.Create a Catalog item to provision a VM on VMware
    3.Order the catalog
    4.Login to SUI and open service details page
    5.Click Access -> VM Console (Make sure in OPS UI Configuration VMware
    Console Support is set to VNC)

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere55_rhel7x():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_vsphere55_fedora27():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere55_win7():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartport5900_endport5902():
    """
    HTML5 tests have Host VNC start and End port settings now in Add
    VMware provider section, specifying the port range limits number of
    Consoles that can be opened simultaneously.We need to check that
    End port - Start Port + 1 = Number of Connections(console) that can be
    opened

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_ie11_vsphere55_win7():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testtype: integration
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_vsphere6_fedora28():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for Firefox Version Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere55_win2012():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat all steps for Firefox version Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_rhv():
    """
    Bugzilla:
        1573739

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere55_win10():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_edge_vsphere6_win10():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartport5955_endport5956():
    """
    HTML5 tests have Host VNC start and End port settings now in Add
    VMware provider section, specifying the port range limits number of
    Consoles that can be opened simultaneously.We need to check that
    End port - Start Port + 1 = Number of Connections(console) that can be
    opened

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartportblank_endportblank():
    """
    Both Start and End ports are blank. So Console will start opening with
    port 5900 and you can open consoles until ports are exhausted.
    UPDATE: I think console is going to be opened on
    port_that_was_last_used + 1. This means it won"t always be 5900.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_edge_rhevm41_win10_spice():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_ssui_win7():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_html5_console_check_consistency_of_behavior():
    """
    Bugzilla:
        1525692

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 3/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_ssui_win7():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
            7. Repeat previous 2 steps in Firefox version latest, latest-1, latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
            7. All should behave the same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_vsphere55_fedora27():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_ssui_fedora():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
            7. Repeat previous 2 steps in Firefox version latest, latest-1, latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
            7. All should behave the same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere6_win7():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere6_rhel7x():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_edge_vsphere55_win10():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_ssui_win10():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
            7. Repeat previous 2 steps in Firefox version latest, latest-1, latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
            7. All should behave the same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_vsphere55_fedora26():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
def test_html5_console_chrome_rhevm41_fedora28_spice():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere55_rhel6x():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere6_win10():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere55_win2012():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_chrome_vsphere6_fedora27():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_firefox_vsphere6_fedora27():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for Firefox Version Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_chrome_vsphere6_win2012():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Chrome
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
def test_html5_console_ie11_ssui_win7():
    """
    1.Login to ssui
    2.provision service
    3.Navigate to the my services and click on "Open a HTML5 console for
    this vm" icon of that service.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Automation-> Automate -> Customization and from
               accordion menu on the left, select Service Dialogs and
               Create a service dialog
            3. Go to Services-> Catalogs, click on Catalog items in
               accordion menu and create a new catalog item using the
               service dialog that you just created
            4. Click on Catalogs in the Accordion menu and create a new
               catalog to hold catalog item created in the previous step
            5. login to self service portal of CFME and order the service catalog
            6. Once service is up and running, you should see a VM running
               for that service, kindly click on Access-> VM Console for
               that VM
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Service dialog should get created and appear in the
               accordion menu under service dialogs
            3. catalog item should be created
            4. new catalog should be created
            5. service request should get created and completed successfully in few mins
            6. VM Console should open and you should be able to interact
               with it with mouse and keyboard
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_ie11_vsphere6_win2012():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on IE
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere6_win7():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
def test_html5_console_chrome_rhevm41_fedora28_vnc():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_firefox_vsphere6_rhel7x():
    """
    HTML5 Test

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 2/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
               4) Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat the steps for the Firefox versions Latest, Latest-1, Latest-2
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Advanced" and then click "Proceed to
               <CFME_URL>(unsafe)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs console should render in the
               HTML5 canvas element and should be able to interact with it
               using mouse & keyboard.
            5. All should behave same
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_with_multiple_nics_each_of_those_two_nic_can_have_only_2_ip_addr():
    """
    OSP: vmware65-Test VM with multiple NICs with single IP (IPv6 to first
    NIC and IPv4 to second)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM with multiple NICs (Each of those two
               NIC can have only 2 IP addresses, 1 IPv4 and 1 IPv6)
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_override_extra_vars_dialog_vsphere():
    """
    1. add tower 2.4.3 provider and perform refresh
    2. Go to job templates
    3. Create service dialog from third_job_template
    - this template is bound to vsphere55 inventory
    - simple_play_4_dockers.yaml playbook is part of this template
    - this playbook will touch /var/tmp/touch_from_play.txt
    - into /var/tmp/touch_from_play_dumped_vars.txt all variables
    available during play run will be dumped
    - this includes also variables passed from Tower or CFME
    - this project is linked with Tower and Vsphere55 credentials
    - Vsphere55 credentials are used when inventory is retrieved
    - Tower credentials are the creds used to login into VM which will be
    deployed
    - Vsphere template used for VM deployment must have ssh key "baked" in
    -
    Prompt for Extra variables must be enabled.
    4. Add Vsphere55 provider into CFME and perform refresh
    5. Create new Catalog
    6. Add new catalog item for Vsphere vcentre - VMWare
    7. give it name, display in catalog, catalog,
    8 Provisioning entry point:
    /Service/Provisioning/StateMachines/ServiceProvision_Template/CatalogI
    temInitialization
    Request info tab:
    Name of template: template_Fedora-Cloud-Base-23-vm-tools_v4 (this
    template has ssh key which matches with Tower creentials)
    VM Name: test_tower_pakotvan_1234 (it must start with test_tower_ -
    inventory script on Tower 2.4.3 was modified to look only for such VMs
    in order to speed up provisioning)
    Envirnment tab:
    - select where VM will be placed and datastore
    Hardware: Select at least 1GB ram for our template
    Network:
    vLAN: VM Network
    9. Automate -> Explorer
    10. Add new Domain
    11. Copy instance Infrastructure->Vm->Provisioning->StateMachines->VMP
    rovision_VM->Provision_VM
    from Template into your domain
    12. Edit this instance
    13. look for PostProvision in the first field/column
    14. Into Value column add:
    /ConfigurationManagement/AnsibleTower/Operations/StateMachines/Job/def
    ault?job_template_name=third_job_template
    15. Automate -> Customization -> Service dialogs -> tower_dialog ->
    Edit this dialog
    Extra variables:
    - make elements in extra variables writable (uncheck readonly).
    - add new element add 1 extra variable - variables must start with
    param_prefix, otherwised will be ignored!!!
    16. Order service
    Into limit field put exact name of your VM:  test_tower_pakotvan_1234
    17. Login into provision VM and `cat
    /var/tmp/touch_from_play_dumped_vars.txt` and grep for variables which
    were passed from CFME UI.

    Polarion:
        assignee: nachandr
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1d
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_azone_disk_io_gce():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(1)
def test_azone_disk_io_azure():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(2)
def test_monitor_ansible_playbook_std_output():
    """
    Bugzilla:
        1444853

    Polarion:
        assignee: apagac
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        title: Monitor Ansible playbook std output
    """
    pass


@pytest.mark.manual
def test_osp_test_cpu_cores_and_sockets_pre_vs_post_migration():
    """
    OSP: Test CPU Cores and Sockets Pre vs Post migration

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test CPU Cores and Sockets Pre vs Post migration
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_distributed_zone_failover_notifier_singleton():
    """
    Notifier (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_dialog_items_default_values_on_different_screens():
    """
    Bugzilla:
        1540273

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
        title: Test dialog items default values on different screens
    """
    pass


@pytest.mark.manual
def test_osp_test_security_group_can_be_selected_while_creating_migration_plan():
    """
    OSP: Test security group can be selected while creating migration plan

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test security group can be selected while creating migration plan
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
@pytest.mark.tier(2)
def test_credentials_change_password_with_special_characters():
    """
    Password with only special characters

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.replication
def test_distributed_diagnostics_servers_view():
    """
    The above should all be shown as different regions 1-4

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_crosshair_op_datastore_vsphere6():
    """
    Requires:
    C&U enabled Vsphere-6 appliance.
    Steps:
    1. Navigate to Datastores [Compute > infrastructure>Datastores]
    2. Select any available datastore
    3. Go for utilization graphs [Monitoring > Utilization]
    4. Check data point on graphs ["Used Disk Space", "Hosts", "VMs"]
    using drilling operation on the data points
    5.  check "chart" and "display" options working properly or not
    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_osp_test_migration_plan_delete():
    """
    OSP: Test migration plan delete

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test migration plan delete
    """
    pass


@pytest.mark.manual
def test_storage_ebs_added_in_ec2_provider():
    """
    Requires:
    test_storage_ebs_added
    Steps to test:
    1. Add an EC2 provider
    2. Wait for refresh
    3. Go to EC2 provider summary
    4. Check whether ebs storage manager is paired with EC2 provider

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/10h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_osp_test_ds_and_volume_availiblity_in_source_and_target():
    """
    OSP: Test DS and Volume availiblity in source and target

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test DS and Volume availiblity in source and target
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_notification_window_can_be_closed_by_clicking_x():
    """
    Bug 1427484 - Add "X" option to enable closing the Notification window
    by it.

    Bugzilla:
        1427484

    After clicking the bell icon in the top right of the web UI, the "x"
    in the top right corner of the notification window can be clicked to
    close it.

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/15h
        startsin: 5.9
        title: Notification window can be closed by clicking 'x'
    """
    pass


@pytest.mark.manual
def test_storage_ebs_volume_crud_from_manager_list():
    """
    Bugzilla:
        1449293

    Requires:
    test_storage_ebs_added
    Steps to test:
    Create:
    1. Go to Storage -> Block Storage -> Block Storage Manager -> Volumes
    Relationship
    2. Add a new cloud volume
    3.Form to fill:
    ec2 EBS Storage Manager
    us-east-1
    volume_test
    Magnetic
    6
    Encryption off
    4. Add
    Read:
    1. Select "volume_test" and go to its summary
    Edit:
    1. Configuration -> Edit this Cloud Volume
    2. Change volume name from "volume_test" to "volume_edited_test"
    3. Select "volume_edited_test" in Block Volume list and go to its
    summary
    Delete:
    1. Configuration -> Delete this Cloud Volume
    2. Check whether volume was deleted

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_osp_test_earlier_infra_mapping_can_be_viewed_in_migration_plan_wizard():
    """
    OSP: Test earlier infra mapping can be viewed in migration plan wizard

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test earlier infra mapping can be viewed in migration plan wizard
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_cluster_graph_by_host_tag_vsphere6():
    """
    test_cluster_graph_by_host_tag[vsphere6]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_cluster_graph_by_host_tag_vsphere65():
    """
    test_cluster_graph_by_host_tag[vsphere65]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(1)
def test_azone_memory_usage_azure():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.retirement
@pytest.mark.tier(2)
def test_retire_cloud_vms_notification_folder():
    """
    test the retire funtion of vm on cloud providers, one vm, set
    retirement date button from vm summary page with notification for two
    vms for one of the period (1week, 2weeks, 1 months)

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_security_group():
    """
    Security group CREATE
    Security group UPDATE
    Security group DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_verify_page_landing_cloud_subnets():
    """
    1. Login To CloudForms Operational Portal
    2. Navigate to compute-> cloud -> instance -> click on any instance ->
    Click on Cloud Networks (under relationships)
    3. Check properly land on page or not.

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/10h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(2)
def test_monitor_ansible_playbook_logging_output():
    """
    bugzilla.redhat.com/1518952

    Bugzilla:
        1518952

    Polarion:
        assignee: apagac
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.8
        title: Monitor Ansible playbook Logging output
    """
    pass


@pytest.mark.manual
def test_candu_collection_tab():
    """
    Test case to cover -
    Bugzilla:
        1393675

    from BZ comments:
    "for QE testing you can only replicate that in the UI by running a
    refresh and immediately destroying the provider and hope that it runs
    into this race conditions."

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
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
        title: OSP: Test migration request details page shows VMs for not started plans
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
@pytest.mark.tier(2)
def test_chargeback_preview():
    """
    Verify that Chargeback Preview is generated for VMs

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
def test_storage_ebs_added():
    """
    Steps to test:
    1. Add an ec2 provider
    2. Go to Storage -> Block Storage -> Managers
    3. Check whether ebs storage manager was added automatically

    Polarion:
        assignee: mmojzis
        caseimportance: critical
        casecomponent: Cloud
        initialEstimate: 1/10h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_azone_network_io_gce():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(1)
def test_azone_network_io_azure():
    """
    Utilization Test

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.replication
def test_distributed_zone_mixed_infra():
    """
    Azure,AWS, and local infra

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_add_multiple_times_ansible_tower_243():
    """
    Try to add same Tower manager twice (use the same IP/hostname). It
    should fail and flash message should be displayed.

    Polarion:
        assignee: nachandr
        caseimportance: medium
        caseposneg: negative
        casecomponent: Ansible
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual('manualonly')
@pytest.mark.tier(1)
def test_infrastructure_provider_left_panel_titles():
    """
    Requirement: Added and infrastructure provider
    Navigate to Compute -> Infrastructure -> Providers
    Select Properties on the panel and check all items, whether they do
    have their titles.
    Select Relationships on the panel and check all items, whether they do
    have their titles.

    Polarion:
        assignee: mmojzis
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/18h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_candu_graphs_host_hourly_vsphere55():
    """
    test_candu_graphs_host_hourly[vsphere55]

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_cluster_tagged_crosshair_op_vsphere65():
    """
    Required C&U enabled application:1. Navigate to cluster C&U graphs
    2. select Group by option with suitable VM/Host tag
    3. try to drill graph for VM/Host

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_cluster_tagged_crosshair_op_vsphere6():
    """
    Required C&U enabled application:1. Navigate to cluster C&U graphs
    2. select Group by option with suitable VM/Host tag
    3. try to drill graph for VM/Host

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(3)
def test_cluster_tagged_crosshair_op_vsphere55():
    """
    Required C&U enabled application:1. Navigate to cluster C&U graphs
    2. select Group by option with suitable VM/Host tag
    3. try to drill graph for VM/Host

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_from_ubuntu():
    """
    OSP: vmware65-Test VM migration from ubuntu

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration from ubuntu
    """
    pass


@pytest.mark.manual
def test_osp_vmware65_test_vm_migration_with_windows_10():
    """
    OSP: vmware65-Test VM migration with Windows 10

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware65-Test VM migration with Windows 10
    """
    pass


@pytest.mark.manual
def test_osp_test_in_progress_migrations_can_be_canceled():
    """
    OSP: Test in-progress Migrations can be canceled

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test in-progress Migrations can be canceled
    """
    pass


@pytest.mark.manual
@test_requirements.tower
def test_config_manager_job_template_refresh():
    """
    After first Tower refresh, go to Tower UI and change name of 1 job
    template. Go back to CFME UI, perform refresh and check if job
    template name was changed.

    Polarion:
        assignee: nachandr
        casecomponent: Ansible
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_osp_test_networking_before_and_after_migration_ip_address():
    """
    OSP: Test networking before and after migration (IP Address)

    Polarion:
        assignee: ytale
        casecomponent: V2V
        caseimportance: critical
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test networking before and after migration (IP Address)
    """
    pass


@pytest.mark.manual
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
        title: OSP: kill the v2v process in the middle- by rebooting
               miq/cfme appliance- should resume migration post restart
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_all():
    """
    Test enabling/disabling all ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -ssh to appliance
               -run appliance_console
               -select option "Update External Authentication Options"
               -select each option to enable it
               -select option
               1) Enable/Disable Single Sign-On
               2) Enable/Disable SAML
               3) Enable/Disable Local Login
               -select "Apply updates"
               -check changes have been made
        startsin: 5.6
        testSteps:
            1. Enable Single Sign-On, SAML, Local Login
            2. Disable Single Sign-On, SAML, Local Login
        expectedResults:
            1. check changes in ui
            2. check changes in ui
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_with_windows_2012_server():
    """
    OSP: vmware67-Test VM migration with Windows 2012 server

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration with Windows 2012 server
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_verify_benchmark_timings_are_correct():
    """
    Bug 1424716 - Benchmark timings are incorrect for all workers in
    evm.log
    Timings logged in evm.log are/seem to be reasonable values:
    [----] I, [2017-09-21T14:53:01.220711 #23936:ded140]  INFO -- :
    MIQ(ManageIQ::Providers::Vmware::InfraManager::Refresher#refresh) EMS:
    [vsphere6], id: [2]
    Refreshing targets for EMS...Complete - Timings
    {:get_ems_data=>0.11566829681396484,
    :get_vc_data=>0.7215437889099121,
    :get_vc_data_ems_customization_specs=>0.014485597610473633,
    :filter_vc_data=>0.0004775524139404297,
    :get_vc_data_host_scsi=>0.5094377994537354,
    :collect_inventory_for_targets=>1.363351821899414,
    :parse_vc_data=>0.10647010803222656,
    :parse_targeted_inventory=>0.10663747787475586,
    :db_save_inventory=>9.141719341278076,
    :save_inventory=>9.141741275787354,
    :ems_refresh=>10.612204551696777}

    Bugzilla:
        1424716

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        title: Verify benchmark timings are correct
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_verify_that_changing_groups_in_the_webui_updates_dashboard_items():
    """
    Verify that switching groups the webui changes the dashboard items to
    match the new groups permissions

    Polarion:
        assignee: apagac
        casecomponent: WebUI
        initialEstimate: 1/4h
        setup: Create a user with two or more groups. The groups should have role
               permissions that grant access to different features so you can easily
               see that the dashboard is updated appropriately.
        startsin: 5.9
        tags: rbac
        title: Verify that changing groups in the webui updates dashboard items
        testSteps:
            1. Login to the OPS webui
            2. Switch to another group
            3. Check that dashboard items are updated appropriately
        expectedResults:
            1. Login successful
            2. Group switch successful
            3. Dashboard items are updated from to reflect that access of the new group
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_resource_average_cpu():
    """
    Validate cost for allocated CPU with "Average" method for allocated
    metrics.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_resource_average_memory():
    """
    Validate cost for allocated memory with "Average" method for allocated
    metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_resource_maximum_cpu():
    """
    Validate cost for allocated CPU with "Maximum" method for allocated
    metrics
    1))Let VM run for a few hours(3- 24 hours)
    2)Sometime during that interval(3-24 hours),reconfigure VM to have
    different resources from when it was created(add/remove
    vCPU,memory,disk)
    3)Validate that chargeback costs are appropriate for vCPU allocated
    when method for allocated metrics is "Maximum".
    Also, see RHCF3-34343, RHCF3-34344, RHCF3-34345, RHCF3-34346,
    RHCF3-34347 .

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_resource_maximum_storage():
    """
    Validate cost for allocated storage with "Maximum" method for
    allocated metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_resource_average_stoarge():
    """
    Validate cost for allocated storage with "Average" method for
    allocated metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_chargeback_cost_resource_maximum_memory():
    """
    Validate cost for allocated memory with "Maximum" method for allocated
    metrics

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_nor_memory_vsphere55():
    """
    Test Normal Operating Range for memory usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 5.5 provider
    Normal Operating Ranges widget displays values for Memory and Memory
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(1)
def test_nor_memory_rhv41():
    """
    Normal Operating Ranges for memory display correctly for RHV 4.1 VM.
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    RHV 4.1 provider
    Normal Operating Ranges widget displays values for Memory and Memory
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.right_size
@pytest.mark.tier(2)
def test_nor_memory_vsphere6():
    """
    Test Normal Operating Range for memory usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays values for Memory and Memory
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_osp_vmware67_test_vm_migration_from_iscsi_storage_in_vmware_to_iscsi_on_osp():
    """
    OSP: vmware67-Test VM migration from iSCSI Storage in VMware to iSCSI
    on OSP

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: vmware67-Test VM migration from iSCSI Storage in VMware to iSCSI on OSP
    """
    pass


@pytest.mark.manual
@test_requirements.storage
def test_storage_volume_backup_restore_from_backup_page_openstack():
    """
    Requires:
    test_storage_volume_backup[openstack]
    1) Navigate to Volume Backups [Storage > Block Storage > Volume
    Backups]
    2) Select respective Volume backups
    3) Restore Volume [configuration > Restore backup to cloud volume
    4) Select Proper Volume to restore
    5) check in Task whether restored or not.

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_credentials_login_password_leading_whitespace():
    """
    Password with leading whitespace

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass
