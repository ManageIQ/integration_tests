# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""

import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream('5.9', '5.10', 'upstream')]


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_domain_import_top_level_directory():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1389823 Importing domain
    from git should work with or without the top level domain directory.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_custom_storage_fields():
    """
    Steps to Reproduce:
    1. Add cloud provider (Openstack) -> Go to Compute-> Clouds->
    Configuration-> Add new cloud provider.
    2. Generate Report -> Go to cloud intel -> Reports-> Configuration->
    Add new report.
    3. Report filters -> Configure Report Columns:
    Base the report on: Cloud Volumes
    Selected Fields:
    -- Cloud Tenant: Name
    --  VMs: Name
    --  VMs: Used Storage
    --  VMs  RAM Size
    --  Vms: Disk 1
    https://bugzilla.redhat.com/show_bug.cgi?id=1499553

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_multiple_servers_uncofigured():
    """
    Verify that buttons unclickable( grayed) when log collection
    unconfigured in all servers under one zone

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1.Configure two appliances to work under one zone
              (distribution mode, one master, another slave)
            2. Open appliance"s WebUi -> Settings -> Configuration
            3. Go to Diagnostics tab -> Collect logs
            4. Select second server (slave) and press "collect" select bar
        expectedResults:
            1.
            2.
            3.
            4. "Collect current logs" and "Collect all logs" grayed and
               became clickable only after configuration log collection
               settings under current server
    """
    pass


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
        casecomponent: cloud
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_status_of_a_task_via_api_with_evmrole_administrator():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1535962

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        tags: rbac
        title: Test status of a task via API with EvmRole_administrator
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_calculating_the_sum_of_a_value_in_a_consolidated_report():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1298298
    Steps to Reproduce:
    1. create a new report on vms & templates
    2. select os name, number of cpus, disk space and other nuerical
    values
    3. consolidate the report by os name and calculate the total of all
    the other value

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
        title: Calculating the sum of a value in a consolidated report
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_against_vmware():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against vmware with vmware credentials

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_check_service_link_from_vm_detail_page():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1443772

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Check service link from VM detail page
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_dashboard():
    """
    Check dashboard view has been added to existing Tower provider screens

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_dialogs_should_only_run_once():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1595776

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Dialogs should only run once
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_error_message_azure():
    """
    Starting with 5.8, error messages generated by azure when provisioning
    from orchestration template will be included in the Last Message
    field.  Users will no longer have to drill down to Stack/Resources to
    figure out the error.
    This is currently working correctly as of 5.8.0.12
    https://bugzilla.redhat.com/show_bug.cgi?id=1410794

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/4h
        setup: Easiest way to do this is provision an azure vm from orchestration
               catalog item and just add a short password like "test".  This will
               fail on the azure side and the error will be displayed in the request
               details.
        startsin: 5.8
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_crud_pod_appliance_custom_config():
    """
    overriding default values in template and deploys pod appliance
    checks that it is alive
    deletes pod appliance

    Polarion:
        assignee: izapolsk
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_rbac_assigning_multiple_tags_from_same_category_to_catalog_item():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1339382

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.5
        title: RBAC : Assigning multiple tags from same category to catalog Item
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_dialog_dropdown_elements_should_honour_defaults():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        startsin: 5.8
        title: Dialog dropdown elements should honour defaults
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_retire_service_with_instances_ec2():
    """
    Retire Service+instances which were deployed by playbook from CFME UI.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_create_simple_aggregated_custom_report():
    """
    Create aggregate custom report.
    Eg: consolidate and aggregate data points into maximum, minimum,
    average, and total.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        title: Create simple aggregated custom report
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_field_zone_description_special():
    """
    Special Chars in description

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_config_manager_provider():
    """
    Add Configuration Manager Provider
    Add tag
    Check item as restricted user

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_playbook_links():
    """
    There are links to repo"s within the playbook table. Clicking in this
    cell will navigate to the details of the Repo.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_childtenant_cloud_memory_quota_by_enforce():
    """
    test memory quota for child tenant for cloud instance by enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_ldap_password_being_logged_in_plain_text_in_evm_log():
    """
    LDAP password being logged in plain text in evm log

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/3h
        title: LDAP password being logged in plain text in evm log
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_datastore_files():
    """
    Check datastore files are fetched correctly

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_remove_default():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the default proxy settings.  For this test you want to create
    an default proxy, verified it worked, and then remove the proxy and
    verify it didn"t use a proxy
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
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
        assignee: None
        casecomponent: cloud
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
        assignee: None
        casecomponent: cloud
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
def test_proxy_remove_azure():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  For this test you want to create an
    azure proxy, verified it worked, and then remove the proxy and verify
    it used the default which may or may not be blank.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify httpd only running when roles require it
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_sui_monitor_ansible_playbook_std_output():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1437210

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : Monitor Ansible playbook Std output
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_change_the_domain_sequence_in_sssd_and_verify_user_groups_retrieval():
    """
    create user1 in test.com
    create group1 in test.com
    assign user1 to group1
    verify for the group retrived for user1
    Only group1 should be displayed in the group list in
    Note:  user should be authenticated with FQDN user1@test.com : group1
    test.com
    user1@qetest.com: qegroup1 qetest.com

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: Change the domain sequence in sssd, and verify user groups retrieval.
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_against_machine_multi_appliance():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against machine with machine credentials. Deploy 2
    appliances, second one as unconfigured, through appliance_console join
    the
    region of first appliance. Enable embedded ansible on 2nd appliance.
    From first appliance, add scm, credentials, new catalog, catalog item
    of AnsiblePlaybook type. Select playbook e.g. dump_all_vars and order
    it. When asked what machine to run it against, pick any rhel7 machine.
    Playbook should be executed successfully.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_black_console_ipa_ntp_negative():
    """
    Try to setup IPA on appliance when NTP daemon is stopped on server.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        setup: -Provision configured appliance
               -ssh into IPA server stop NTP daemon
               -ssh into new appliance
               -try setting up IPA (https://mojo.redhat.com/docs/DOC-1058778)
               -after testing remember to start NTP daemon again
    """
    pass


@pytest.mark.manual
def test_appliance_terminates_unresponsive_worker_process():
    """
    If a queue message consumes significant memory and takes longer than
    the 10 minute queue timeout, the appliance will kill the worker after
    the stopping_timeout.
    Steps to test:
    https://bugzilla.redhat.com/show_bug.cgi?id=1395736#c30
    https://bugzilla.redhat.com/show_bug.cgi?id=1395736#c31

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
        title: Appliance terminates unresponsive worker process
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_childtenant_cloud_vm_quota_by_enforce():
    """
    test no of vms quota for child tenant for cloud instance by
    enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_cockpit_connected():
    """
    Prerequisitiies:
    Appliance connected to provider
    Installed Cockpit on VM present on connected provider
    VM running
    Cockpit accesible on vm_ip:9090
    Navigate to Compute > Infrastructure > Virtual Machines
    Find VM with Cockpit running and accessible and go to its detail
    Navigate to Access > Web console
    # Web Console is active
    Select Web Console
    # browser is redirected to Cockpit web page on VM
    Go to VM and disable Cockpit daemon
    Go to appliance, find VM with Cockpit running and accessible and go to
    its detail
    Navigate to Access > Web console
    # Web Console is disabled
    Go to VM and enable Cockpit daemon
    Go to appliance, find VM with Cockpit running and accessible and go to
    its detail
    Navigate to Access > Web console
    # Web Console is enabled

    Polarion:
        assignee: nansari
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_copy_provisioning_dialog():
    """
    Automate - customization - provisioning dialog
    Create a new dialog. Save
    Configuration - Copy this dialog .

    Polarion:
        assignee: None
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Copy provisioning dialog
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_capture_vm_event_azure():
    """
    capture vm event[azure]

    Polarion:
        assignee: None
        caseimportance: low
        initialEstimate: 1/4h
        title: capture vm event[azure]
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_user_cloud_storage_quota_by_services():
    """
    test user storage quota for cloud instance provision by ordering
    services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_export_all_existing_dialogs_almost_100_dialogs():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1570298
    Steps to Reproduce:
    1. Go to Automation -> Automate -> Customization -> Select Import
    Export
    2. Select all existing dialogs (almost 100 dialogs)
    3. Press the button "Export"
    4. After some time, the error 502 appears.
    5. Individual or sometimes a group of dialogs can be exported

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Export all existing dialogs (almost 100 dialogs
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
@test_requirements.ansible
def test_embed_tower_playbooks():
    """
    playbooks included under ansible shown in a table view (automation-
    ansible-playbooks)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_cmqe_delete_existing_resource_quota():
    """
    Delete existing Resource Quota

    Polarion:
        assignee: juwatts
        caseimportance: medium
        initialEstimate: 1h
        title: CMQE - Delete Existing Resource Quota
        testSteps:
            1. &nbsp;Delete the&nbsp;existing Resource Quota that was added in&nbsp;&nbsp;
            2. Refresh the CFME appliance
            3. Check the containers_quota_items table in the database
            4. Navigate to the namespace in the CFME GUI.
        expectedResults:
            1. Verify the Resource Quota was deleted successfully
            2. Appliance refreshed successfully.
            3. Verify the deleted Resource Quotas should still exist, with
               `deleted_on` field set.
            4. Verify the GUI displays no data referencing Resource Quota.
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
def test_public_ip_without_nic_azure():
    """
    Relates to https://bugzilla.redhat.com/show_bug.cgi?id=1531099  -
    Update testcase after BZ gets resolved
    Update: we are not filtering PIPs but we can use PIPs which are not
    associated to any NIC
    1. Have a Puplic IP on Azure which is not assigned to any Network
    Interface - such Public IPs should be reused property
    2. Provision Azure Instance - select public IP from 1.

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_rhos_test_notification_for_snapshot_delete_failure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1581793
    Test if cfme can report failure when deleting snapshot from RHOS.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        title: RHOS: test notification for snapshot delete failure
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_users():
    """
    Check users are fetched correctly for analysed VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_rhi_appliance():
    """
    Red Hat Insights:
    Register an Appliance to RHSM or Satellite.
    Perform SmartState Analysis on appliance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_datastore_files_unicode():
    """
    Make sure https://bugzilla.redhat.com/show_bug.cgi?id=1221149 is fixed

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_external_database_appliance():
    """
    Configure appliance to use external DB

    Polarion:
        assignee: tpapaioa
        casecomponent: config
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_data_processor():
    """
    C & U Data Processor (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_stack_service_vm_detail_page_should_show_correct_data():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1467569

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : Stack Service VM detail page should show correct data
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_notification_for_snapshot_actions_on_openstack():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1429313
    Test task notification for snapshot tasks: success and failure of
    create and delete snapshot.

    Polarion:
        assignee: apagac
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1h
        title: Test notification for snapshot actions on OpenStack
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu instance.
    3. Check Groups are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Groups  are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Groups are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_rhos7_ga_fedora_22_ext4():
    """
    test_ssa_groups[rhos7-ga-fedora-22-ext4]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Groups are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_groups_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
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
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_email_should_be_sent_when_service_approval_is_set_to_manual():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1380197

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Email should be sent when service approval is set to manual
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_infra_storage_quota_by_services():
    """
    test group storage for infra vm provision by ordering services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_infrastructure_hosts_icons_states():
    """
    Requirement: Added a RHEVM provider
    Then do in console:
    su - postgres
    psql
    \c vmdb_production
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
        assignee: mmojzis
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_should_allow_selecting_multiple_items_in_a_service_dialog_element_with_multiselec():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1539862

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        initialEstimate: 1/16h
        title: SUI should allow selecting multiple items in a Service
               Dialog element with Multiselect enabled
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_provision_more_than_15_vms_for_gce():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1337646

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.5
        title: provision more than 15 VM's  for GCE
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
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_init_processes():
    """
    Check init services are fetched correctly for analysed VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_black_console_ipa_negative():
    """
    test setting up authentication with invalid host settings

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_packages():
    """
    Check packages are fetched correctly for analysed VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_sui_create_snapshot_from_vm_details_page_snapshot_page_and_service_details_page():
    """
    Snapshot can be created from VM details page , service details page
    and snapshot page .
    Check all pages and the snapshot count displayed on vm details page .

    Polarion:
        assignee: apagac
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: SUI : Create snapshot from vm details page, snapshot page
               and service details page
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_cloud_storage_quota_by_lifecycle():
    """
    test group storage quota for cloud instance provision by Automate
    model

    Polarion:
        assignee: ghubale
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_validate_chargeback_cost_weekly_rate_network_cost():
    """
    Validate network I/O used cost in a daily Chargeback report by
    assigning weekly rate

    Polarion:
        assignee: nachandr
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(2)
def test_log_scvmm_settings_scvmm():
    """
    In configuration\server\advanced you can set the log level for the
    azure specific scvmm.log file.  Need to changes the values and verify
    that the correct info is recording.  For this test, at least set it to
    DEBUG.
    tail -f scvmm.log | grep --line-buffered ERROR or WARN or something.

    Polarion:
        assignee: anikifor
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(2)
def test_quota_with_invalid_service_request():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1531914 Test quotas with
    various regions and invalid service requests
    This bug contains the steps to follow:
    https://bugzilla.redhat.com/show_bug.cgi?id=1534589
    To reproduce this issue: (You"ll need to have the RedHat Automate
    domain)
    1. Setup multiple zones.(You can use a single appliance and just add a
    "test" zone)
    2. Add VMWare provider and configure it to the "test" zone.
    3. Create a VMWare Service Item.
    4. Order the Service.
    5. Delete the Service Template used in the Service creation in step 3.
    6. Modify the VMWare provider to use the default zone. (This should
    leave the existing Service request(s) in the queue for the "test" zone
    and the service_template will be invalid)
    7. Provision a VMWare VM.
    You should see the following error in the log:
    "[----] E, [2018-01-06T11:11:20.073924 #13027:e0ffc4] ERROR -- :
    Q-task_id([miq_provision_787]) MiqAeServiceModelBase.ar_method raised:
    <NoMethodError>: <undefined method `service_resources" for
    nil:NilClass>
    [----] E, [2018-01-06T11:11:20.074019 #13027:e0ffc4] ERROR -- :
    Q-task_id([miq_provision_787]) "

    Polarion:
        assignee: ghubale
        casecomponent: control
        initialEstimate: 1/4h
        startsin: 5.9
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
@pytest.mark.tier(2)
def test_template_info_scvmm2016():
    """
    The purpose of this test is to verify that the same number of
    templates in scvmm are in cfme.  Take the time to spot check a random
    template and check that the details correspond to SCVMM details.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_reconfigure_vm_vmware_cores_multiple():
    """
    Test changing the cpu cores of multiple vms at the same time.

    Polarion:
        assignee: sshveta
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -get new configured appliance
               -add vmware provider
               -provision 2 new vms
               -power off 1 vm
               -select both vms
               -configure-->reconfigure vm
               -increase/decrease counts
               -power on vm
               -check changes
        startsin: 5.6
        testSteps:
            1. Hot increase
            2. Hot Decrease
            3. Cold Increase
            4. Cold Decrease
            5. Hot + Cold Increase
            6. Hot + Cold Decrease
        expectedResults:
            1. Action should fail
            2. Action should fail
            3. Action should succeed
            4. Action should succeed
            5. Action should fail
            6. Action should Error
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_cloud_memory_quota_by_services():
    """
    test group memory quota for cloud instance provision by ordering
    services

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
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
        casecomponent: prov
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
@test_requirements.cfme_tenancy
def test_tenant_unique_catalog():
    """
    Catalog name is unique per tenant. Every tenant can have catalog with
    name "catalog" defined.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
def test_pdf_summary_infra_provider():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1651194
    1. Add an Infrastructure Provider (tested with VMware)
    2. Open the summary page of the provider
    3. In the toolbar click "Print or export summary"
    = Quadicon is shown correctly, exactly as in the UI

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        initialEstimate: 1/8h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_retirement_remove_resources():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1501143
    Description of problem:
    It"s not possible to have "Remove resources?" field with "No" value in
    Ansible Playbook catalog item
    Steps to Reproduce:
    1. Open creation screen of Ansible Playbook catalog item.
    2. Fill required fields.
    3. Open Retirement tab.
    4. Fill "Remove resources?" field with "No" value.
    5. Press "Save" button.
    Actual results:
    In details screen of the catalog item "Remove resources?" has "Yes".
    Expected results:
    "Remove resources" should have correct value.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_user_quota_vm_reconfigure():
    """
    Create User quota
    assign some quota limitations
    recongifure VM over limit.

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_configure_external_auth_for_ldaps_with_sssdconf_for_single_ldaps_domain():
    """
    Look for the steps/instructions at
    https://mojo.redhat.com/docs/DOC-1085797
    Verify appliance_console is updated with “External Auth: “ correctly

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
        title: Configure External auth for ldaps with sssd.conf for single ldaps domain
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
        casecomponent: candu
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
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_should_generate_with_no_errors_in_logs():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1592480#c21

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/2h
        startsin: 5.9
        title: Reports should generate with no errors in logs
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_verify_change_update_in_ldap_server_takes_effect_in_the_cfme_authentication():
    """
    Change user/groups attribute in  ldap domain server.
    E.g change user display name
    Verify authentication fails for old display name
    Verify authentication for new display name for the user.
    Verify changing cache_credentials = True
    entry_cache_timeout = 600

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: Verify change/update in ldap server takes effect in the CFME authentication.
    """
    pass


@pytest.mark.manual
@test_requirements.rep
def test_distributed_add_provider_to_remote_zone():
    """
    Adding a provider from the global region to a remote zone.

    Polarion:
        assignee: tpapaioa
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_role_configured_with_the_option_only_user_or_group_owned_should_allow_to_access_to_se():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1554775

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: Role configured with the option "only user or group owned"
               should allow to access to service catalogs and items
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_cloud_cpu_quota_by_services():
    """
    test group cpu quota for cloud instance provision by ordering services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_that_non_admin_users_can_view_catalog_items_in_ssui():
    """
    Verify user with a non-administrator role can login to the SSUI and
    view catalog items that are tagged for them to see
    See https://bugzilla.redhat.com/show_bug.cgi?id=1465642
    Note: in order for this to work, all ownership limitations must be
    removed.

    Polarion:
        assignee: apagac
        casecomponent: ssui
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
@pytest.mark.tier(2)
def test_shutdown_guest_scvmm():
    """
    This test performs the Shutdown Guest from the LifeCycle menu which
    invokes the Hyper-V Guest Services Integration command.  This
    gracefully exits the Windows OS rather than just powering off.
    From collections page, select the VM and click "Shut down guest"
    On SCVMM powershell, use "$vm = Get-VM -name "name_of_vm"; Find-SCJob
    -objectId $vm.id -recent" to verify VM history shows "Shut down
    virtual machine" instead of "power off"

    Polarion:
        assignee: ghubale
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
def test_custom_button_display_ssui_single():
    """
    Test custom button display for single/detail page for SSUI

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
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
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_failover():
    """
    Check that ansible fails over to new region correctly

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_scm_credentials():
    """
    Add SCM credentials for private GIT repo.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_regions_disable_azure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1412355
    CloudForms should be able to enable/disable unusable regions in Azure,
    like the Government one for example.

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/10h
        setup: You will need to go into advanced settings and add or remove items
               from the following section.
               :ems_azure:
               :disabled_regions:
               - usgovarizona
               - usgoviowa
               - usgovtexas
               - usgovvirginia
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_generic_objects_class_accordion_should_display_when_locale_is_french():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1594480

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.10
        title: Generic objects class accordion should display when locale is french
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_ui_pinning_after_relog():
    """
    Go to Automate -> Explorer
    Pin this menu
    Logout
    Log in
    No menu should be pinned

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_triggered_refresh_shouldnt_occurs_for_dialog_after_changing_type_to_static():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1614436

    Polarion:
        assignee: None
        casecomponent: services
        initialEstimate: None
        title: Triggered Refresh shouldn't Occurs for Dialog After Changing Type to Static
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_childtenant_cloud_storage_quota_by_enforce():
    """
    test storage quota for child tenant for cloud instance by enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_notification_banner_vm_provisioning_notification_and_service_request_should_be_in_syn():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1389312

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Notification Banner - VM Provisioning Notification and
               Service Request should be in  Sync
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_retirement_now_scvmm():
    """
    Verify that a VM can be retired immediately.  This should work whether
    the VM is running or not, so repeat this test with a vm that is
    running and a vm that is off.  Note that the VM is no longer removed
    with later versions

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_patches_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Patches are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_patches_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 R2 server VM.
    Check whether Patches are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_patches_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Patches are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
def test_ec2_deploy_cfme_image():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1413835
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
        casecomponent: appl
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
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_persistent_volumes():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1563861

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
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
@test_requirements.service
@pytest.mark.tier(3)
def test_timepicker_should_show_date_when_chosen_once():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1638079

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: None
        title: Timepicker should show date when chosen once
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_field_zone_description_long():
    """
    When creating a new zone, the description can be up to 50 characters
    long, and displays correctly after saving.

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
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
def test_cmqe_modify_existing_resource_quota():
    """
    Modify Existing Quota

    Polarion:
        assignee: juwatts
        caseimportance: medium
        initialEstimate: 1h
        title: CMQE - Modify Existing Resource Quota
        testSteps:
            1. Modify the existing Resource Quota that was added in &nbsp;
            2. Refresh the CFME appliance
            3. Check the containers_quota_items table in the database
            4. Navigate to the namespace in the CFME GUI.
            5. Modify the existing Resource Quota again
            6. Refresh the CFME appliance
            7. Check the containers_quota_items table in the database
            8. Navigate to the namespace in the CFME GUI.
        expectedResults:
            1. Verify the update was successful
            2. Appliance refreshed successfully.
            3. Verify the modified values (eg. increased cpu) should appear
               as multiple rows — old value with `deleted_on` field set,
               and new value with approximately same `created_at`.
            4. Verify the GUI displays the correct data and the fractional
               values are formatted properly.
            5. Verify the update was successful
            6. Appliance refreshed successfully.
            7. Verify multiple values with both (created_at, deleted_on)
               set and only last one with deleted_on=null.
            8. Verify the GUI displays the correct data and the fractional
               values are formatted properly.
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_user_cloud_memory_quota_by_lifecycle():
    """
    test user memory quota for cloud instance provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_reconfigure_add_disk_cold():
    """
    Test adding 16th disk to test how a new scsi controller is handled.
    https://bugzilla.redhat.com/show_bug.cgi?id=1337310

    Polarion:
        assignee: sshveta
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.7
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1565128
    After saving VM retirement date/time (using both "Specific Date and
    Time" and "Time Delay from Now" options), the displayed Retirement
    Date has the correct date and time-zone appropriate time.

    Polarion:
        assignee: tpapaioa
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/15h
        startsin: 5.9
        title: Retirement date uses correct time zone
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_monitor_resources():
    """
    Check there is a method for monitoring embedded ansibles resource
    usage.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/10h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_check_default_value_setting_for_all_options_in_dialog():
    """
    Cannot set default option for static dropdown list in Service Dialog -
    https://bugzilla.redhat.com/show_bug.cgi?id=1471964

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        title: Check default value setting for all options in Dialog
    """
    pass


@pytest.mark.manual
@test_requirements.rep
def test_distributed_zone_add_provider_to_nondefault_zone():
    """
    Can a new provider be added the first time to a non default zone.

    Polarion:
        assignee: tpapaioa
        casecomponent: infra
        caseimportance: critical
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_automate_buttons_requests():
    """
    Navigate to Automate -> Requests
    Check whether these buttons are displayed:
    Reload
    Apply
    Reset
    Default

    Polarion:
        assignee: anikifor
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/18h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_saml_verify_user_login_with_and_without_correct_groups_added_to_saml_server():
    """
    Create cfme default groups in saml server.
    Assign user to the default groups. e.g.  EvmGroup-administrator
    Configure cfme for ldaps external auth as in TC#1
    Authentication for ldap user is expected to be successful as cfme
    default groups are already assigned for user in saml server.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
        title: saml: verify user login with and without correct groups added to SAML server.
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_orchestration_link_mismatch():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1601523

    Polarion:
        assignee: sshveta
        casecomponent: stack
        caseimportance: medium
        initialEstimate: 1/4h
        title: orchestration link mismatch
    """
    pass


@pytest.mark.manual
@test_requirements.control
@pytest.mark.tier(3)
def test_control_import_with_incorrect_schema():
    """
    Test importing yaml with incorrect schema.

    Polarion:
        assignee: mmojzis
        casecomponent: control
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(2)
def test_log_azure_settings_azure():
    """
    In configuration\server\advanced you can set the log level for the
    azure specific azure.log file.  Need to changes the values and verify
    that the correct info is recording.  For this test, at least set it to
    DEBUG.
    tail -f azure.log | grep --line-buffered ERROR or WARN or something.

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_zone_unconfigured():
    """
    check collect all logs under zone when both levels are unconfigured.
    Expected result - all buttons are disabled

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_cloud_volume_types():
    """
    Test CloudVolumeType endpoint. Add a cloud provider and check if it
    gives correct response for the GET request.
    GET /api/cloud_volume_types
    GET /api/cloud_volume_types/:id
    PR: https://github.com/ManageIQ/manageiq-api/pull/465

    Polarion:
        assignee: pvala
        initialEstimate: None
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_storage_provider_children():
    """
    1. Tag provider
    2. Login as restricted user
    3. Check Providers children visibility
    Expected result: Providers children should not be visible for
    restricted user

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
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
        casecomponent: candu
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vm_mac_scvmm():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1514461
    Test case covers this BZ - we can"t get MAC ID of VM at the moment

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/20h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1514461
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
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_import_invalid_file():
    """
    import invalid file like txt, pdf.
    Import yaml file with wrong data.
    Flash message should display if we import wrong file.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_navigation_with_18000_tags():
    """
    create > 18000 tags, Make navigation to services
    No error should occur

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_custom_button_state_hidden():
    """
    If the expression of visibility is true then the button will be in
    enabled(unhidden) state but if it is false then it will be in the
    hidden state.
    Steps:
    1. Add provider
    2. Create service dialog
    3. Create custom button group in service accordion option
    5. Add button to the group. In "Advanced" tab of button, put valid
    expression for Visibility (Make sure to select dialog created at
    step2)
    6. Create catalog from Services
    7. Create catalog item and assign dialog & catalog created in step2 &
    6 respectively.
    8. Navigate to self-service UI and Order created catalog item
    9. Click service you have ordered and you will notice button will
    disappear.
    (Better practice will be carried test_custom_button_state_enabled
    first and then try out this)
    Expression used while test: COUNT OF Service.User.VMs < -1
    Additional info:
    This enhancement feature is related to https://github.com/ManageIQ
    /manageiq-ui-service/pull/1012.

    Polarion:
        assignee: ndhandre
        casecomponent: ssui
        caseimportance: low
        initialEstimate: None
        startsin: 5.9
        upstream: no
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
        assignee: mkourim
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
def test_custom_button_access_ssui():
    """
    Test custom button for role access of SSUI

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_delete_occupied():
    """
    Delete Zone that has appliances in it.

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_quota_source_user():
    """
    When copying and modifying
    /System/CommonMethods/QuotaStateMachine/quota to user the user as the
    quota source and when the user is tagged, the quotas are in effect.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_can_add_child_tenant_to_tenant():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1387088
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
        casecomponent: config
        initialEstimate: 1/10h
        tags: rbac
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_regions_all_azure():
    """
    Need to validate the list of regions we show in the UI compared with
    regions.rb  Recent additions include UK South
    These really don"t change much, but you can use this test case id
    inside bugzilla to set qe_test flag.

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.6
        upstream: yes
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_attach_iso_vsphere67_nested():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1533728

    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.provision
@pytest.mark.tier(2)
def test_azure_instance_password_requirements_azure():
    """
    Create provision request with password which doesn"t meet requirements
    - warning message should appear in UI
    Additional details are in
    https://bugzilla.redhat.com/show_bug.cgi?id=1454812
    The supplied password must be between 8-123 characters long and must
    satisfy at least 3 of password complexity requirements from the
    following:
    1) Contains an uppercase character
    2) Contains a lowercase character
    3) Contains a numeric digit
    4) Contains a special character.

    Polarion:
        assignee: jhenner
        casecomponent: prov
        caseposneg: negative
        initialEstimate: 1/10h
        testtype: nonfunctional
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_network_adapters_vsphere67_nested_vmkernel():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/16h
        startsin: 5.9
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
        casecomponent: ssui
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
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_server_server_setup():
    """
    using any type of depot check collect all log function under applince
    (settings under applince should be configured, under zone should not
    be configured)

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
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
@pytest.mark.tier(1)
def test_webmks_console_edge_vsphere67_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_ie11_vsphere65_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere67_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere65_rhel7x():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: critical
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere65_fedora27():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere65_fedora27():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_passwordwithspecialchars():
    """
    VMware WebMKS Remote Console Test based on
    https://bugzilla.redhat.com/show_bug.cgi?id=1545927

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: critical
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere65_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere6_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere65_fedora26():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere6_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere67_fedora26():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere67_rhel7x():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: critical
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere6_fedora27():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere6_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere67_fedora28():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere6_rhel7x():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere65_fedora28():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere67_rhel7x():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: critical
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere65_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere67_fedora26():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere6_fedora26():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere67_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_edge_vsphere65_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere67_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere65_rhel7x():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: critical
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_ie11_vsphere65_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_edge_vsphere6_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere67_fedora28():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere6_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere6_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_ie11_vsphere67_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere65_fedora26():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere65_fedora28():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere6_fedora28():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere65_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere67_fedora27():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere6_fedora26():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere65_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere6_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_ie11_vsphere67_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere6_fedora28():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_ie11_vsphere6_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere6_rhel7x():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere67_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere67_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere67_fedora27():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_chrome_vsphere6_fedora27():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere65_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere65_win10():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_firefox_vsphere67_win2012():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_webmks_console_ie11_vsphere6_win7():
    """
    VMware WebMKS Remote Console Test

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
               Note: [XX-YY-ZZ] stands for ->
               XX: Browser
               YY: Platform or SSUI-Self Service UI
               ZZ: OS
        startsin: 5.8
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
        assignee: None
        casecomponent: cloud
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
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_infra_memory_quota_by_lifecycle():
    """
    test group memory quota for infra vm provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_default_dialog_entries_should_localized_when_ordering_catalog_item_in_french():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1592573

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        title: Default dialog entries should localized when ordering catalog item in French
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_instance():
    """
    Instance CREATE
    Instance RUNNING
    Instance STOPPED
    Instance UPDATE
    Instance DELETE \ Instance Terminate

    Polarion:
        assignee: mmojzis
        casecomponent: cloud
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
        casecomponent: ssui
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
@test_requirements.report
@pytest.mark.tier(1)
def test_create_and_run_custom_report_using_rbac():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1526058

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
def test_configure_diagnostics_pages_cfme_region():
    """
    Go to Settings -> Configuration -> Diagnostics -> CFME Region
    and check whether all sub pages are showing.

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/15h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_stdout():
    """
    User/Admin is able to execute playbook and see stdout of it once
    completed.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
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
@test_requirements.config_management
def test_config_manager_accordion_tree():
    """
    Make sure there is accordion tree, once Tower is added to the UI.
    https://bugzilla.redhat.com/show_bug.cgi?id=1560552

    Polarion:
        assignee: nachandr
        casecomponent: web_ui
        caseimportance: low
        initialEstimate: None
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
        casecomponent: report
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
        assignee: None
        casecomponent: optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_ec2_api_filter_limit():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1612086
    The easiest way to simulate AWS API Limit for > 200 items is to enable
    and disable public images:
    Requirement: Have an ec2 provider
    1) Enable public images for ec2 in Advanced Settings
    2) Wait for public images to be refreshed
    3) Disable public images for ec2 in Advanced Settings
    4) Wait for public images to be refreshed (cleared)

    Polarion:
        assignee: None
        casecomponent: cloud
        initialEstimate: 1 1/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_reconfigure_add_disk_cold_controller_sas():
    """
    Steps to Reproduce:
    1. Add 15 disks to an existing VM with Controller type set to SAS
    2. look at the 16th Disk Controller Type
    Expected results: Should be SAS like exiting Controller
    https://bugzilla.redhat.com/show_bug.cgi?id=1445874

    Polarion:
        assignee: nansari
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_host_credentials_web():
    """
    Validate that web connections to the host can be created.

    Polarion:
        assignee: None
        casecomponent: infra
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
@pytest.mark.tier(1)
def test_automate_simulate_retry():
    """
    PR Link
    Automate simulation now supports simulating the state machines.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
        setup: Create a state machine that contains a couple of states from which one
               of them retries at least once.
        startsin: 5.6
        testSteps:
            1. Use automate simulation UI to call the state machine (Call_Instance)
        expectedResults:
            1. A Retry button appears.
    """
    pass


@pytest.mark.manual
def test_diagnostic_timelines():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
def test_group_quota_via_ssui():
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_black_console_ext_auth_options():
    """
    Test enabling ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -ssh to appliance
               -run appliance_console
               -select option "Update External Authentication Options"
               -select each option to enable it
               -select option
               1) Enable Single Sign-On
               2) Enable SAML
               3) Enable Local Login
               -select "Apply updates"
               -check changes have been made
        startsin: 5.6
        testSteps:
            1. Enable Single Sign-On
            2. Enable SAML
            3. Enable Local Login
        expectedResults:
            1. check changes in ui
            2. check changes in ui
            3. check changes in ui
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(2)
def test_embed_ansible_next_gen():
    """
    Follow BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1511126

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.10
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_cloud_storage_quota_by_services():
    """
    test group storage quota for cloud instance provision by ordering
    services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tagvis_vm_and_template():
    """
    Enable one or multiple VM's and Template's in the group and check for
    the visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_ui_notification_icon():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1489798
    1) Go to rails console and type:
    Notification.create(:type => :automate_user_error, :initiator =>
    User.first, :options => { :message => "test" })
    2) Check in UI whether notification icon was displayed
    3) Go to rails console and type:
    Notification.create(:type => :automate_global_error, :initiator =>
    User.first, :options => { :message => "test" })
    4) Check in UI whether notification icon was displayed

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: low
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_can_add_project_to_tenant():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1387088
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
        casecomponent: config
        initialEstimate: 1/10h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.quota
def test_service_bundle_provsioning_with_quota_enabled():
    """
    test_service_bundle_provsioning_with_quota_enabled

    Polarion:
        assignee: ghubale
        casecomponent: prov
        initialEstimate: 1/4h
        setup: 1.create a catalog item of type vmware
               2.create a catalog bundle by adding the above resource.
               3.make sure CloudForms quotas are enabled
               4.provision the bundle
        startsin: 5.8
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
@test_requirements.config_management
def test_no_rbac_warnings_in_logs_when_viewing_satellite_provider():
    """
    RBAC-related warnings logged when viewing Satellite provider in web UI
    https://bugzilla.redhat.com/show_bug.cgi?id=1565266
    1.) Add Satellite provider.
    2.) Click on items under Providers accordion.
    3.) View evm.log. No WARN-level messages should be logged.
    [----] W, [2018-04-09T14:09:19.654859 #13384:84e658]  WARN -- :
    MIQ(Rbac::Filterer#lookup_method_for_descendant_class) could not find
    method name for ConfiguredSystem::ConfiguredSystem

    Polarion:
        assignee: tpapaioa
        casecomponent: prov
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
        casecomponent: cloud
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
        assignee: None
        casecomponent: optimize
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
@test_requirements.config_management
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
        casecomponent: prov
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
@test_requirements.service
@pytest.mark.tier(3)
def test_database_wildcard_should_work_and_be_included_in_the_query():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1581853

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: None
        startsin: 5.10
        title: Database wildcard should work and be included in the query
    """
    pass


@pytest.mark.manual
def test_user_should_be_able_to_see_requests_irrespective_of_tags_assigned():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1641012

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        startsin: 5.9
        title: User should be able to see requests irrespective of tags assigned
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(2)
def test_tenant_visibility_service_template_catalogs_all_parents():
    """
    Members of child tenants can see service templates which are visible
    in parent tenants.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_ssui_myservice_myrequests_and_service_catalog_filter_links():
    """
    Filter Links of all pages

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        endsin: 5.6
        initialEstimate: 1/8h
        startsin: 5.5
        title: SSUI : MyService, MyRequests and Service Catalog - Filter Links
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_refresh_ssui_page():
    """
    Upon logging into the SSUI, Hit F5, the page should refresh, but
    previously this action logged the user out.

    Polarion:
        assignee: nansari
        casecomponent: ssui
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_host_vm_combination():
    """
    Combine My Company tag tab restriction, with Clusters&Host tab and
    VM&templates
    User should be restricted to see tagged host and vm, template

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(2)
def test_tenant_visibility_services_all_childs():
    """
    Members of parent tenant can see services of all child tenants.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_create_generic_class():
    """
    Automation - automate - Generic Object - create new generic class .
    test Generic class with different associations , attributes and
    methods .

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: create generic class
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_against_rhos():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against RHOS with RHOS credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tagvis_cluster_change():
    """
    Enable / Disable a Cluster in the group and check its visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
def test_simultaneous_tenant_quota():
    """
    Test multiple tenant quotas simultaneously
    https://bugzilla.redhat.com/show_bug.cgi?id=1456819
    https://bugzilla.redhat.com/show_bug.cgi?id=1401251

    Polarion:
        assignee: ghubale
        casecomponent: prov
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(3)
def test_distributed_migrate_embedded_ansible_role():
    """
    Ansible role failsover/migrates when active service fails

    Polarion:
        assignee: tpapaioa
        casecomponent: infra
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
@test_requirements.tag
@pytest.mark.tier(2)
def test_tagvis_vm_and_template_modified():
    """
    Enable / Disable a VM's and Template's in the group and check its
    visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_validate_cost_weekly_usage_memory():
    """
    Validate cost for memory usage for a VM in a weekly chargeback report

    Polarion:
        assignee: tpapaioa
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_reports_custom_tags():
    """
    Add custom tags to report
    1)add custom tags to appliance using black console
    ssh to appliance, vmdb; rails c
    use following commands
    cat = Classification.create_category!(name: "rocat1", description:
    "read_only cat 1", read_only: true)
    cat.add_entry(name: "roent1", description: "read_only entry
    1")2)Create new or Edit existing report and look for the tag category
    in list of columns.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_in_dynamic_dropdown_list_the_default_value_should_not_contain_all_the_values_of_the_l():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1568440

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: In dynamic dropdown list, the default value should not
               contain ALL the values of the list
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_snapshots_for_vm_create_edit_delete():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.8
        title: SUI : Snapshots for VM (Create/Edit/delete)
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenant_osp_mapping_refresh():
    """
    There is new feature in 5.7, mapping of Openstack tenants to CFME
    tenants.
    1) switch"Tenant Mapping Enabled" checkbox to Yes when adding RHOS
    cloud provider
    2) create new test tenant in RHOS
    2) perform refresh of RHOS provider in CFME UI
    3) new tenants are created automatically

    Polarion:
        assignee: mnadeem
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_submit_or_cancelation_buttons_in_dynamic_dialogs_tied_to_a_service_button_should_be_v():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1611527

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/6h
        title: Submit or cancelation buttons in dynamic dialogs tied to a
               Service button should be visble
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_notification_for_snapshot_delete_failure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1449243
    Requires ec2 access via web-ui.

    Polarion:
        assignee: apagac
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/4h
        title: test notification for snapshot delete failure
        testSteps:
            1. Create a snapshot on EC2 provider
            2. Try to delete snapshot via CFME UI
        expectedResults:
            1. Snapshot created
            2. Snapshot not deleted and notification displayed
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_authentication_user_created_after_success_login():
    """
    Configure CFME for LDAP authentication and add group. Authenticate
    with LDAP user and check if user exists in Configuration - Access
    Control - Users.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
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
        casecomponent: candu
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
        casecomponent: candu
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
@test_requirements.service
@pytest.mark.tier(2)
def test_change_provider_template_in_catalog_item():
    """
    test_change_provider_template_in_catalog_item

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        testSteps:
            1. Create a catalog item and select template for a provider in catalog tab
            2. Select datastore etc in environment tab
            3. In catalog tab change template from one provider to another
        expectedResults:
            1.
            2.
            3. Validation message should be shown
    """
    pass


@pytest.mark.manual
def test_custom_button_crud_via_rest():
    """
    In this Test case we verify the functionality of custom button using
    rest api
    Steps
    1) POST method to create the custom button
    2) POST method to edit the custom button
    3) Delete method to delete the custom button

    Polarion:
        assignee: ndhandre
        initialEstimate: None
        startsin: 5.9
        upstream: yes
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
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_custom_conditional_filter_report():
    """
    Steps to Reproduce: ===================
    1. Create a service with one of the above naming conventions (vm-test
    ,My-Test)
    2. Have at least one VM in the service so the reporting will parse it
    3. Create a report with a conditional filter in it, such as:
    conditions: !ruby/object:MiqExpression exp: and: - IS NOT NULL: field:
    Vm.service-name - IS NOT NULL: field: Vm-ems_cluster_name 3. Run the
    report
    https://bugzilla.redhat.com/show_bug.cgi?id=1521167

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_log_collection_via_ftp_over_ipv6():
    """
    Bug 1452224 - Log Collection fails via IPv6
    https://bugzilla.redhat.com/show_bug.cgi?id=1452224
    An IPv6 FTP server can be validated for log collection, and log
    collection succeeds.
    # subscription-manager register
    # subscription-manager attach --pool 8a85f98159d214030159d24651155286
    # yum install vsftpd
    # vim /etc/vsftpd/vsftpd.conf
    anon_upload_enable=YES
    anon_mkdir_write_enable=YES
    # ip6tables -F
    # setenforce 0
    # systemctl start vsftpd
    # mkdir /var/ftp/pub/anon
    # chmod 777 /var/ftp/pub/anon
    Administrator > Configuration > Diagnostics > Collect Logs > Edit
    Type        Anonymous FTP
    Depot Name    tpapaioa
    URI        ftp://localhost6/pub/anon
    > Save
    Collect > Collect current logs
    Refresh after a couple minutes
    Basic Info
    Log Depot URI        ftp://localhost6/pub/anon
    Last Log Collection    2018-01-10 20:29:31 UTC
    Last Message        Log files were successfully collected

    Polarion:
        assignee: None
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        title: Log collection via FTP over IPv6
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_crud_repo():
    """
    CRUD repo.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_sdn_nsg_firewall_rules_azure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1520196
    1. Add Network Security group on Azure with coma separated port ranges
    `1023,1025` rule inbound/outbound ( ATM this feature is not allowed in
    East US region of Azure - try West/Central)
    2. Add such Azure Region into CFME
    3. Refresh provider
    4. Open such NSG in CFME and check that ports from 1) do present in
    the UI as Firewall rules

    Polarion:
        assignee: mmojzis
        casecomponent: cloud
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
        assignee: mkourim
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_new_dialog_editor_all_element_types_ui_and_validations():
    """
    Check all element types for the new dialog editor

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        startsin: 5.9
        title: New dialog editor - All element types UI and validations
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_embed_tower_refresh_provider_repo_list():
    """
    Test if ansible playbooks list is updated in the UI when "Refresh
    Selected Ansible Repositories" clicked in the repository list.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_embed_tower_refresh_provider_repo_details():
    """
    Test if ansible playbooks list is updated in the UI when "Refresh this
    Repository" clicked in the repository details view.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(1)
def test_utilization_utilization_graphs():
    """
    Polarion:
        assignee: None
        casecomponent: optimize
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
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_field_zone_name_special():
    """
    When creating a new zone, special characters can be used in the name,
    including leading and trailing characters, and the name displays
    correctly in the web UI after saving.

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(2)
def test_tenant_visibility_providers_all_parents():
    """
    Child tenants can see providers which were defined in parent tenants.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.5
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
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/16h
        setup: Create a orchestration template and provision a stack from it .
               Delete the template
        startsin: 5.5
        title: Delete orchestration template in use
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(2)
def test_embed_tower_invisible():
    """
    Embedded Ansible Tower provider won"t be visible in the CFME UI (Tower
    should be headless, its UI should not be enabled.) p1

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_cmqe_add_new_resource_quota():
    """
    Add new resource quota

    Polarion:
        assignee: juwatts
        caseimportance: medium
        initialEstimate: 1h
        title: CMQE - Add New Resource Quota
        testSteps:
            1. On the Openshift provider, create different namespaces and
               assign them Resource Quotas. Assign different fractional
               values to the CPU quotas like  `1.152` or `0.087` or `87m`.
            2. Refresh the CFME appliance
            3. Check the containers_quota_items table in the database
            4. Navigate to the namespace in the CFME GUI.
            5. Refresh the CFME appliance
            6. Check the containers_quota_items table in the database
        expectedResults:
            1. Resource Quota assigned successfully.
            2. Appliance refreshed successfully.
            3. Database in `container_quota_items` table should contain
               both old and current values.            Newly added quotas
               should have `created_at` field set.
            4. Verify the GUI displays the correct data and the fractional
               values are formatted properly.
            5. Appliance refreshed successfully.
            6. Verify duplicate records were not added to the table
    """
    pass


@pytest.mark.manual
@test_requirements.chargeback
def test_service_chargeback_retired_service():
    """
    Validate Chargeback costs for a retired service

    Polarion:
        assignee: nachandr
        casecomponent: report
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
        casecomponent: cloud
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
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_order_and_request_should_be_sorted_by_time():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.8
        title: SUI : Order and Request should be sorted by time
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(2)
def test_notification_show_notification_when_tenant_quota_is_reached():
    """
    when quota is soon to be reached,CFME should notify affected users

    Polarion:
        assignee: ghubale
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.8
        title: Notification : Show notification when tenant quota is reached
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_cluster_combination():
    """
    Combine My Company tag tab restriction, with Clusters&Host tab
    Visible cluster should match both tab restrictions

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_in_the_self_service_portal_reconfigure_service_should_shows_available_provisioning_di():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1633453

    Polarion:
        assignee: nansari
        casecomponent: ssui
        initialEstimate: 1/2h
        title: In the self service portal, reconfigure service should shows
               available Provisioning Dialog
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
@test_requirements.quota
@pytest.mark.tier(1)
def test_service_infra_tenant_quota_storage_default_entry_point():
    """
    tenant service storage quota validation for infra provider using
    default entry point

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_groups():
    """
    Check groups are fetched correctly for analysed VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_service_cloud_tenant_quota_memory_default_entry_point():
    """
    tenant service memory quota validation for cloud provider using
    default entry point

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.8
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
        assignee: mmojzis
        casecomponent: web_ui
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_saving_a_service_dialog_with_a_multi_select_drop_down_populated_by_expression_method_():
    """
    Saving a service dialog with a multi-select drop-down populated by
    expression method gives a 500 internal server error
    https://bugzilla.redhat.com/show_bug.cgi?id=1559030

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Saving a service dialog with a multi-select drop-down
               populated by expression method should not error
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_sui_reconfigure_service_from_sui():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
        title: SUI : Reconfigure service from SUI
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_multiple_vms():
    """
    Perform SSA on multiple VMs.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_windows2016_disk_fileshare():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server R2 VM having disk located on
    Fileshare.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_windows2016_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2012 R2 server Instance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_windows2012r2_refs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_customer_scenario():
    """
    This test case should be checked after each CFME release.(which
    supports EC2 SSA)
    Add EC-2 provider.
    Perform SSA on instance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_rhos7_ga_fedora_22_ext4():
    """
    test_ssa_vm[rhos7-ga-fedora-22-ext4]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_schedule():
    """
    Trigger SmartState Analysis via schedule on VM.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_second_disk_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having
    NTFS as Primary Disk filesystem and secondary disk ReFS filesystem.
    It should pass without any error.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm():
    """
    Make sure SSA can be started on a VM for configured provider
    (parametrized)

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_compliance_policy():
    """
    Checks compliance condition on VM/Instance which triggers Smartstate
    Analysis on VM/Instance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_vsphere6_nested_wimdows7_xfs_ssui():
    """
    1. Provision service with Windows 7 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_compliance_policy():
    """
    Checks compliance condition on VM/Instance which triggers Smartstate
    Analysis on VM/Instance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_multiple_vms():
    """
    Perform SSA on multiple VMs.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_schedule():
    """
    Trigger SmartState Analysis via schedule on VM.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_managed_disk():
    """
    Perform SSA on Managed disk on Azure provider.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_windows2012_ssui():
    """
    1. Provision service with Windows 2012 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_rhel():
    """
    Create or Use existing RHEL VM/Instance present in Azure.
    Perform SSA on RHEL VM/Instance when
    VM/Instance is Powered ON
    VM/Instance is Powered OFF

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.6
        upstream: no
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_wimdows2016_ssui():
    """
    1. Provision service with Windows 2016 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_windows2016_refs():
    """
    This test is to verify that you get an error when trying to perform
    SSA on a Windows2016 VM that has a ReFS formatted disk attached.  Here
    is the before and after.
    05/26/17 18:13:36 UTC
    05/26/17 18:10:56 UTC
    05/26/17 18:10:46 UTC
    finished
    Unable to mount filesystem. Reason:[ReFS is Not Supported]
    Scan from Vm ReFS16on16a
    admin
    EVM
    Scanning completed.
    05/26/17 16:12:45 UTC
    05/26/17 16:08:30 UTC
    05/26/17 16:08:26 UTC
    finished
    Process completed successfully
    Scan from Vm ReFS16on16a
    admin
    EVM
    Synchronization complete

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
        setup: Need to create a windows 2016 instance and save it onto the ReFS disks
               on Azure.
               Add a second disk to the VM config.  Open VM, initialize disk and
               format it as ReFS
               Refresh you CFME appliance
               Perform SSA on that VM.
               Best to just use existing ReFS vms.
        startsin: 5.6
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_multiple_vms():
    """
    Perform SSA on multiple VMs.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_region():
    """
    1. Add an Azure Instance in one region and assign it to a Resource
    Group from another region.
    BZ link: https://bugzilla.redhat.com/show_bug.cgi?id=1503295

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_windows2016_refs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_ubuntu_ssui():
    """
    1. Provision service with Ubuntu VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_wimdows2012_ssui():
    """
    1. Provision service with Windows 2012 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Cross-check whether smartstate instance created from AMI mentioned in
    production.yml.
    BZ:https://bugzilla.redhat.com/show_bug.cgi?id=1547228

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_agent_tracker():
    """
    BZ link:  https://bugzilla.redhat.com/show_bug.cgi?id=1557452

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_windows2012r2_refs():
    """
    This test is to verify that you get an error when trying to perform
    SSA on a Windows2012 r2 instance that has a ReFS formatted disk
    attached.  Here is the before and after.
    05/26/17 18:13:36 UTC
    05/26/17 18:10:56 UTC
    05/26/17 18:10:46 UTC
    finished
    Unable to mount filesystem. Reason:[ReFS is Not Supported]
    Scan from Vm ReFS16on16a
    admin
    EVM
    Scanning completed.
    05/26/17 16:12:45 UTC
    05/26/17 16:08:30 UTC
    05/26/17 16:08:26 UTC
    finished
    Process completed successfully
    Scan from Vm ReFS16on16a
    admin
    EVM
    Synchronization complete

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseposneg: negative
        initialEstimate: 1/2h
        setup: Need to create a windows 2012r2 instance and save it onto the ReFS
               disks on Azure.
               Add a second disk to the VM config.  Open VM, initialize disk and
               format it as ReFS
               Refresh you CFME appliance
               Perform SSA on that VM.
               Best to just use existing ReFS vms.
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_vsphere6_nested_centos_xfs_ssui():
    """
    1. Provision service with CentOS VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_ubuntu():
    """
    Perform SSA on Ubuntu VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_windows2012r2_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_non_managed_disk():
    """
    Perform SSA on non-managed (blod) disk on Azure provider.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_windows2016_disk_fileshare():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server R2 VM having disk located on
    Fileshare..

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure_ubuntu_ssui():
    """
    1. Provision service with Ubuntu VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_second_disk_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server R2 VM having
    NTFS as Primary Disk filesystem and secondary disk ReFS filesystem.
    It should pass without any error.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_schedule():
    """
    Trigger SmartState Analysis via schedule on VM.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_windows2016_ssui():
    """
    1. Provision service with Windows 2016 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_disk_usage():
    """
    1. Add a VMware provider
    2. Run SSA for the VM and the data store (might not be necessary, but
    wanted to make sure all data collection is executed)
    3. Navigate to a VM
    4. Click on "number of disks"

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_cancel_task():
    """
    Start SSA on VM and wait snapshot to create.
    Cancel the task immediately.
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1538347

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_scvmm2k16_compliance_policy():
    """
    Checks compliance condition on VM/Instance which triggers Smartstate
    Analysis on VM/Instance.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_azure():
    """
    Perform SSA on Instance on States:
    1. Power ON
    2. Power OFF.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_ec2_vpc():
    """
    1. Create a VPC;
    2. Do not attach any gateway to it;
    3. Turn on "DNS resolution", "DNS hostname" to "yes";
    4. Deploy an agent on this VPC;
    5. Run SSA job;
    BZ link: https://bugzilla.redhat.com/show_bug.cgi?id=1557377

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_vm_collect_running_processes_neg():
    """
    Same as 9570, only Verify that you CANNOT extract the running
    processes from a VM with a Linux Guest OS that is running and has an
    IP Address.
    The Extract Running Processes menu item should be grey when a Linux VM
    is selected.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_ui_requests_notifications_negative():
    """
    After all processes are running make sure websockets are enabled then
    add a repo with the same name as a current repo and check the
    notifications display correctly. With a Red banner to show it was
    unsuccessful.
    https://bugzilla.redhat.com/show_bug.cgi?id=1471868

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_openstack_provider_has_dashboard():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1487142

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        initialEstimate: 1/4h
        startsin: 5.10
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_automate_ansible_playbook_method_type_verbosity():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1542665
    Check if ansible playbook method  can work with different verbosity
    levels.

    Polarion:
        assignee: dmisharo
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(2)
def test_tenant_visibility_miq_requests_all_childs():
    """
    Tenant members can see MIQ requests of this tenant and its children.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.5
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/10h
        title: Session purging occurs only when session_store is sql
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_actions():
    """
    Check SSA can be a part of action for VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_drop_down_dialog_should_honor_the_order_of_values_as_they_are_inputted():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1593874

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/16h
        startsin: 5.9
        title: Drop Down Dialog should Honor the Order of Values as they are Inputted
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenant_osp_mapping_delete():
    """
    Tenants created by tenant mapping cannot be deleted.
    1) Add rhos which has at least one tenant enabled and perform refresh
    2) Navigate to Configuration -> Access Control -> tenants
    3) Try to delete any of the tenants created by tenant mapping process
    4) This is not possible until RHOS provider is removed from VMDB
    5) try this again after provider is removed

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_customize_request_security_group():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1335989

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_authentication_ldap_switch_groups():
    """
    Test whether user who is member of more LDAP groups is able to switch
    between them

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_host_credentials_default():
    """
    Verified that the Host Default credential can be set in order to allow
    Collect Running Processes to get the processes from a VM>

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_aws_smartstate_pod():
    """
    deploy aws smartstate pod and that it works

    Polarion:
        assignee: izapolsk
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_repo_tag():
    """
    RBAC - tag Ansible repo and allow new user see only this repo.
    https://bugzilla.redhat.com/show_bug.cgi?id=1526217

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_custom_button_openurl_vm():
    """
    Refer custom button mojo FAQ for more detail.
    Additional info - https://bugzilla.redhat.com/show_bug.cgi?id=1602023

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        initialEstimate: 1/8h
        startsin: 5.10
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_create_appliance_on_scvmm_using_the_vhd_image():
    """
    Log into qeblade33 and download the VHD appliance image.  Create a new
    VM, attach the VHD disk, and boot system.

    Polarion:
        assignee: None
        casecomponent: appl
        initialEstimate: 1/4h
        subtype1: usability
        title: Create Appliance on SCVMM using the VHD image.
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
def test_satellite_host_groups_show_up_as_configuration_profiles_satellite_62():
    """
    For the Satellite provider satellite_62, both the centos and fedora-
    cloud configuration profiles show up in Configuration > Manage, in the
    accordion menu under All Configuration Manager Providers > Red Hat
    Satellite Providers > satellite_62 Configuration Manager.

    Polarion:
        assignee: tpapaioa
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/15h
        title: Satellite host groups show up as Configuration Profiles [satellite_62]
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_with_already_existing_catalog_item_name():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1509809

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_external_auth_details_updated_in_appliance_console_ipa_():
    """
    Run appliance_console and verify external_auth details are correctly
    updated for IPA

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify external_auth details updated in appliance_console[IPA].
    """
    pass


@pytest.mark.manual
def test_dynamic_dropdowns_should_show_value_only_once():
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Dynamic dropdowns should show value only once
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_group_actions():
    """
    Test the SUI snapshot timeline.
    Test grouping of actions in a timeline. Try to create a couple of
    snapshots in a rapid succession, check how it looks in the timeline.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/3h
        testSteps:
            1. create a new vm
            2. create multiple snapshots in fast succession (two should be enough)
            3. go to the VM details page, then Monitoring -> Timelines
            4. select "Management Events" and "Snapshot Activity" and click Apply
            5. click on the group of events in timeline
        expectedResults:
            1. vm created
            2. snapshots created
            3. timelines page displayed
            4. group of events displayed in the timeline
            5. details of events displayed, correct number of events
               displayed, time/date seems correct
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_dynamic_dropdown_multiselect_default_element_is_shouldnt_be_blank_when_loaded_by_anot():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1645555
    https://bugzilla.redhat.com/show_bug.cgi?id=1645555

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/16h
        title: Dynamic Dropdown Multiselect: Default element is shouldn't
               be blank when loaded by another element
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_expression_method_definitions_should_not_fail_with_script_error_in_a_dialog():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1558926

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/6h
        startsin: 5.10
        title: Expression method definitions should not fail with "" in a dialog
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
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_test_all_language_translations():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : Test all Language translations
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_verbosity():
    """
    BZ 1460788
    Check if the different Verbosity levels can be applied to service and
    monitor the std out

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_update_yum_bad_version_59017():
    """
    Tests appliance update between versions
    Test Source

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_vm_request_approval_by_user_in_different_group():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1545395

    Polarion:
        assignee: apagac
        casecomponent: infra
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
        assignee: None
        casecomponent: optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.discovery
@pytest.mark.tier(1)
def test_domain_id_required_validation():
    """
    Steps:1. Try to add OpenStack provider
    2. Select Keystone V3 as for it only we need to set domain id
    3. don"t fill domain id
    4. Verify
    5. check for flash
    https://bugzilla.redhat.com/show_bug.cgi?id=1545520

    Polarion:
        assignee: pvala
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_the_columns_for_the_custom_attribute_should_have_their_values_in_report():
    """
    Steps to Reproduce:
    1. set a custom attribute on a VM with a space in the name
    2. set a custom attribute on a VM with a colon in the name
    3. Create a report with the VM name and the two custom attributes
    4. run the report
    https://bugzilla.redhat.com/show_bug.cgi?id=1553750

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        title: The columns for the custom attribute should have their values in report
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_vmware_provider_filters():
    """
    N-3 filters for esx provider.
    Example: ESXi 6.5 is the current new release.
    So filters for 6.5 (n), 6.0 (n-1), 5.5 (n-2) at minimum.

    Polarion:
        assignee: None
        casecomponent: prov
        caseimportance: low
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_saml_sso_works_fine_check_both_enable_disable_options():
    """
    Configure external auth as in TC#1 and enable SSO option.
    Verify SSO option works fine.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/4h
        title: Verify SAML SSO works fine, check both enable/disable options.
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_dialog_text_box_triggers_fields_shouldnt_refresh_too_soon_often():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1614321

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: None
        startsin: 5.10
        title: Dialog text box triggers fields shouldn't refresh too soon / often
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_mixed_appliance_ip_versions():
    """
    IPv6 and IPv4 appliances

    Polarion:
        assignee: tpapaioa
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_appliance_scsi_control_vmware():
    """
    Appliance cfme-vsphere-paravirtual-*.ova has SCSI controller as Para
    Virtual

    Polarion:
        assignee: None
        casecomponent: appl
        caseimportance: critical
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_dynamic_check_box_does_not_update_in_classic_ui():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1570152

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.8
        title: Dynamic check box does not update in Classic UI
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
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_import_multiple_domains():
    """
    Import of multiple domains from a single git repo is not allowed

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_cui_should_check_dialog_field_associations():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1559382

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/6h
        title: CUI Should check dialog field associations
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_ldap_group_lookup_fails_with_correct_error_message_for_invalid_user_details():
    """
    verify ldap group lookup fails with correct error message for invalid
    config details.
    1. configure ldap.
    2. specify wrong user details while group look up, verify group lookup
    fails with correct error message.
    refer the BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1378213

    Polarion:
        assignee: apagac
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        title: verify ldap group lookup fails with correct error message
               for invalid user details
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_new_vm():
    """
    Test the SUI snapshot timeline.
    See if there"s no timeline when there"s no snapshot.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/6h
        testSteps:
            1. create a new vm
            2. go to the VM details page, then Monitoring -> Timelines
            3. select "Management Events" and "Snapshot Activity" and click Apply
        expectedResults:
            1. vm created
            2. timelines page displayed
            3. no timeline visible, warning "No records found for this timeline" displayed
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_repo_links():
    """
    test clicking #of playbooks cell will navigate to the Playbooks area,
    filtered by the associated repo name.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
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
@test_requirements.service
@pytest.mark.tier(3)
def test_changing_action_order_in_catalog_bundle_should_not_removes_resource():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1615853

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/16h
        title: Changing action order in catalog bundle should not removes resource
    """
    pass


@pytest.mark.manual
def test_rhn_mirror_role_packages():
    """
    Test the RHN mirror role by adding a repo and checking if the contents
    necessary for product update got downloaded to the appliance

    Polarion:
        assignee: jkrocil
        casecomponent: appl
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
@pytest.mark.tier(1)
def test_sdn_nsg_arrays_refresh_azure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1520196
    1. Add Network Security group on Azure with coma separated port ranges
    `1023,1025` rule inbound/outbound ( ATM this feature is not allowed in
    East US region of Azure - try West/Central)
    2. Add such Azure Region into CFME
    3. Refresh provider

    Polarion:
        assignee: mmojzis
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_duplicate_order_does_not_provision_service():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.8
        title: SUI : Duplicate order does not provision service
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provider_flavors_azure():
    """
    Verify that the vm flavors in Azure are of the correct sizes and that
    the size display in CFME is accurate.  This test checks a regression
    of https://bugzilla.redhat.com/show_bug.cgi?id=1357086
    Low priority as it is unlikely to change once set.  Will want to check
    when azure adds new sizes.  Only need to spot check a few values.
    For current size values, you can check here:
    https://azure.microsoft.com/en-us/documentation/articles/virtual-
    machines-windows-sizes/

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.6
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_against_amazon():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against Amazon EC2 with EC2 credentials
    enable Embedded Ansible
    wait until it is enabled and add repository with playbooks
    add AWS EC2 credentials
    create new catalog
    add new catalog item with EC2 playbook
    order the service and wait for it"s execution
    check if service was finished OK

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_control_icons_simulation():
    """
    Requirements: Have an infrastructure provider
    Go to Control -> Simulation
    Select:
    Type: Datastore Operation
    Event: Datastore Analysis Complete
    VM Selection: By Clusters, Default
    Submit
    Check for all icons in this page

    Polarion:
        assignee: anikifor
        casecomponent: control
        caseimportance: medium
        initialEstimate: 1/15h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_show_quota_used_on_tenant_quota_screen_even_when_no_quotas_are_set():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1415792

    Polarion:
        assignee: ghubale
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
        title: Test show quota used on tenant quota screen even when no quotas are set
        testSteps:
            1. Add multiple providers and check the tenant quota screen
               and check in use quota
        expectedResults:
            1. quota  in "In use" column should reflect the correct count
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_market_place_images_azure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1491330
    1.Enable market place images
    2.Verify the list of images

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/6h
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
        initialEstimate: 1/5h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_add_branch_repo():
    """
    Ability to add repo with branch (without SCM credentials).

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenant_ssui_users_can_see_their_services():
    """
    Self Service UI - users can see their services
    1) Configure LDAP authentication on CFME
    1) Create 2 different parent parent-tenants
    - marketing
    - finance
    2) Create groups marketing and finance (these are defined in LDAP) and
    group names in LDAP and CFME must match
    Assign these groups to corresponding tenants and assign them EvmRole-
    SuperAdministrator roles
    3) In LDAP we have 3 users:
    - bill -> member of marketing group
    - jim -> member of finance group
    - mike -> is member of both groups
    4) add rhos/amazon providers and refresh them
    - BUG: if provider with the same IP is added to CFME already it is not
    seen in Cloud - Providers and it cannot be added again.
    Therefore you have to add 2 different providers as a workaround.
    Providers must be added under corresponding tenants!!!
    5) login as bill and create new catalog with  - finance_catalog and
    catalog item
    - catalog items cannot contain fields which requires input from users?
    -known limitation based on information from Brad"s presentation - this
    is for froms that have dynamic dialogs items
    6) login as jim and create new catalog with EC2 item
    7) login as jim or bill, you should see catalog items of parent-
    tenants and  for tenant they are in, mike user should see items from
    marketing or finance catalog based on which group is active in Classic
    UI
    - this does not work well - in SSUI - My Services and My requests does
    not show any items (correct) but number of services/requests is
    calculated also from services not relevant to actual tenant - this is
    fixed in next RC

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.rep
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
        casecomponent: appl
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_playbook_with_already_existing_dialogs_name():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1449345

    Polarion:
        assignee: sshveta
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/4h
        title: Test Playbook with already existing dialog's name
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_notification_banner_service_event_should_be_shown_in_notification_bell():
    """
    1) OPS UI  and SSUI service requests should create an event in
    notification bell
    2) Also check , Clear All and "MArk as read" in notification bell
    3) Number of events shown in notification bell

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Notification Banner : Service event should be shown in notification bell
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
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_create_generic_instance():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1577395

    Polarion:
        assignee: nansari
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
        title: Create generic Instance
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_utilization_provider():
    """
    Verify гutilication data from providers

    Polarion:
        assignee: None
        casecomponent: optimize
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1445928
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/10h
        startsin: 5.7
        title: pg_stat_activity view in postgres should show worker information
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_disable():
    """
    Test disabling ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -ssh to appliance
               -run appliance_console
               -select option "Update External Authentication Options"
               -select each option to enable it
               -select option
               1) Disable Single Sign-On
               2) Disable SAML
               3) Disable Local Login
               -select "Apply updates"
               -check changes have been made
        startsin: 5.6
        testSteps:
            1. Disable Single Sign-On
            2. Disable SAML
            3. Disable Local Login
        expectedResults:
            1. check changes in ui
            2. check changes in ui
            3. check changes in ui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_reconfigure_service_fields_empty_after_deploying_service():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1580987

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Reconfigure service fields empty after deploying service
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_reporting():
    """
    Reporting (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
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
        assignee: mkourim
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(3)
def test_cloud_tenant_link():
    """
    verify clicking cloud Tenant field in cloud image summary page

    Polarion:
        assignee: anikifor
        casecomponent: appl
        caseimportance: low
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_relationship_trailing_spaces():
    """
    PR Link (Merged 2016-04-01)
    Handle trailing whitespaces in automate instance relationships.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/10h
        setup: A fresh appliance.
        startsin: 5.6
        testSteps:
            1. Create a class and its instance, also create second one,
               that has a relationship field. Create an instance with the
               relationship field pointing to the first class" instance but
               add a couple of whitespaces after it.
            2. Execute the AE model, eg. using Simulate.
        expectedResults:
            1.
            2. Logs contain no resolution errors
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_network_adapters_vsphere67_nested_dportgroup():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/16h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_network_adapters_vsphere67_nested_mgmtnetwork():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/16h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_network_adapters_vsphere67_nested_vmnetwork():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/16h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_custom_reports_with_timelines_policy_events2():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
def test_custom_reports_with_timelines_vm_operation():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.timelines
@pytest.mark.tier(2)
def test_custom_reports_with_timelines():
    """
    Cloud Intel->Reports allows to copy existing reports with timelines or
    create new ones from scratch.
    Such custom reports appear in Cloud Intel -> Timelines after creation.

    Polarion:
        assignee: None
        casecomponent: report
        caseimportance: low
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
def test_custom_reports_with_timelines_hosts():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
def test_custom_reports_with_timelines_policy_events():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
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
def test_crud_pod_appliance_ansible_deployment():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance

    Polarion:
        assignee: izapolsk
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_ssui_dynamic_dropdown_values_are_not_loaded_in_dropdown_unless_refresh_button_is_pres():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1322594

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: SSUI : Dynamic dropdown values are not loaded in dropdown
               unless refresh button is pressed
    """
    pass


@pytest.mark.manual
@test_requirements.control
@pytest.mark.tier(3)
def test_control_policy_simulation_displayed():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1550503
    Test if policy simulation is displayed

    Polarion:
        assignee: mmojzis
        casecomponent: control
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_look_up_ldap_groups_option_works_fine():
    """
    verify Look Up LDAP Groups option works fine.
    1. configure external auth
    2. navigate to "configuration -> Access Control -> Groups -> Add new
    group"
    3. Check the option "Look Up LDAP Groups" and verify retrieve groups
    works fine.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        title: verify Look Up LDAP Groups option works fine.
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
        casecomponent: appl
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
@test_requirements.report
@pytest.mark.tier(1)
def test_report_import_export_widgets():
    """
    Import and  Export widgets

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/16h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
def test_custom_button_automate_ssui():
    """
    Test custom button with automation request method

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        initialEstimate: 1/8h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_data_collector():
    """
    C & U Data Collector (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_dialog_value_type_integer_string_check_in_dropdown_elements():
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Dialog : value type(Integer/string) check in dropdown elements
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_cloud_memory_quota_by_lifecycle():
    """
    test group memory quota for cloud instance provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_rhi_inventory():
    """
    Verify various tabs by applying filters on one or more systems

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
def test_single_custom_button_disable():
    """
    Steps 1.Create a custom button (Unassigned Button) for services
    2.Provide an Enablement expression for disabling the custom button.
    (e.g: COUNT OF Service.VMs > 5000 )
    3.Add "Disabled Button Text"
    4.Click on save
    5.Login on to SSUI page
    6.Goto Service and check the button is disabled
    7.Hover over button to check the disable text.
    Additional Information:
    https://bugzilla.redhat.com/show_bug.cgi?id=%201502304 Use the above
    BZ link for understand the [RFE]

    Polarion:
        assignee: ndhandre
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_project_cloud_storage_quota_by_enforce():
    """
    test storage quota for project for cloud instance by enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_generic_object_service_associations():
    """
    Use the attached domain to test this bug:
    1) Import end enable the domain
    2) Have at least one service created (Generic is enough)
    3) Run rails console and create the object definition:
    GenericObjectDefinition.create(
    :name => "LoadBalancer",
    :properties => {
    :attributes   => {:location => "string"},
    :associations => {:vms => "Vm", :services => "Service"},
    }
    )
    4) Run tail -fn0 log/automation.log | egrep "ERROR|XYZ"
    5) Simulate Request/GOTest with method execution
    In the tail"ed log:
    There should be no ERROR lines related to the execution.
    There should be these two lines:
    <AEMethod gotest> XYZ go object: #<MiqAeServiceGenericObject
    ....something...>
    <AEMethod gotest> XYZ load balancer got service:
    #<MiqAeServiceService:....something....>
    If there is "XYZ load balancer got service: nil", then this bug was
    reproduced.
    thx @lfu

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
def test_custom_button_in_sui():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1450473
    https://bugzilla.redhat.com/show_bug.cgi?id=1454910

    Polarion:
        assignee: ndhandre
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        title: Test Custom button in SUI
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_automate_git_domain_displayed_in_dialog():
    """
    Check that the domain imported from git is displayed and usable in the
    pop-up tree in the dialog editor.
    You can use eg. https://github.com/ramrexx/CloudForms_Essentials.git
    for that

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        initialEstimate: 1/15h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_user_validation_works_fine_but_authentication_fails_if_no_group_is_assigned_fo():
    """
    Create user in ldap domain server.
    Do not assign any group to the user.
    Configure cfme for ldaps external auth as in TC#1
    Validation for ldap user is expected to be successful but the
    authentication should fail as there is no group for the user.
    Check audit.log and evm.log for “unable to match user"s group
    membership to an EVM role” message.
    Verify this scenario by "Get User Groups from External Authentication
    (httpd)" option ENABLED and DISABLED.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        title: verify user validation works fine but authentication fails
               if no group is assigned for user.
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
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_cloud_credentials():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1444092When the service is
    viewed in my services it should also show that the cloud credentials
    were attached to the service.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: low
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_rhi_unregister():
    """
    Verify Unregisteration of system by selecting one or more systems from
    list

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_repo_list():
    """
    After all processes are running add a few repo"s for playbooks. Check
    that all these repos appear in the repo list section in the ui, With
    the correct status and the correct quantity of playbooks.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_disabled_domains_in_domain_priority():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1331017 When the admin
    clicks on a instance that has duplicate entries in two different
    domains. If one domain is disabled it is still displayed in the UI for
    the domain priority.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
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
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_engine_database_connection():
    """
    All steps in: https://bugzilla.redhat.com/show_bug.cgi?id=1334909

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
def test_configuration_region_description_change():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1350808 Go to Settings
    -> Configure -> Settings
    Details -> Region
    Change region description
    Check whether description was changed

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/20h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(3)
def test_import_duplicate_report():
    """
    This case tests appliance behaviour when a duplicate report is
    imported.
    Steps:
    1) Create a custom report.
    2) Go to Import/Export accordion and click on `Custom Reports`.
    3) Export the available report(newly created custom report from step
    1).
    4) Import the same exported yaml file.
    Expected Result:
    A flash message should appear: `Skipping Report (already in DB):
    [report_name]`

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
def test_ec2_add_delete_add_provider():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: cloud
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
def test_pod_appliance_start_stop():
    """
    appliance should start w/o issues

    Polarion:
        assignee: izapolsk
        initialEstimate: None
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_event_catcher_collect():
    """
    EventCatcher process collects all activity from api/acitivity_streamis
    and is writing data into PG DB

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_zone_all_unconfigured():
    """
    check collect logs under zone when both levels are unconfigured.
    Expected result - all buttons are disabled

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
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
        casecomponent: config
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
@test_requirements.ssui
@pytest.mark.tier(3)
def test_generic_object_should_be_visible_in_service_view():
    """
    Generic object should be visible in service view

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1515945
        startsin: 5.9
        title: Generic object should be visible in service view
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_custom_service_dialog_quota_flavors():
    """
    Test quota with instance_type in custom dialog
    https://bugzilla.redhat.com/show_bug.cgi?id=1499193

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_custom_button_on_resource_detail_ssui():
    """
    Steps:
    1. Add custom button under service option (from automation > automate
    > customization > service accordion)
    2. In normal UI - OPS, Provision test service using any infra provider
    (nvc55 recommended)
    3. In SSUI, Check custom button on VM resource details page
    Additional info: https://bugzilla.redhat.com/show_bug.cgi?id=1427430

    Polarion:
        assignee: ndhandre
        casecomponent: ssui
        initialEstimate: None
        startsin: 5.9
        tags: ssui
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_order_credentials_usecredsfromservicedialog():
    """
    Test if creds from Service Dialog are picked up for execution of
    playbook or the default are used(that were set at the time of dialog
    creation)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tagvis_ldap_group_host():
    """
    Add LDAP group, assign a host permission and check for the visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_attribute_override():
    """
    Steps to Reproduce:
    1. create a custom button to request the call_instance_with_message
    2. set the message to create
    3. set the attributes instance, class, namespace to "whatever"
    4. set the attribute message to "my_message"
    5. save it
    Reference BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1651099

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_pod_appliance_config_upgrade():
    """
    appliance config update should cause appliance re-deployment

    Polarion:
        assignee: izapolsk
        caseimportance: medium
        initialEstimate: None
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
        assignee: None
        caseimportance: medium
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
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_in_dynamic_multi_select_dialog_elements_the_first_element_shouldnt_be_selected_when_n():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1576288

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/6h
        title: In Dynamic multi select dialog elements the first element
               shouldn't be selected when nil default is specified
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_machine_credentials_service_details_opsui():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1515561  When the service
    is viewed in my services it should also show that the cloud and
    machine credentials were attached to the service.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_machine_credentials_service_details_sui():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1540689  When the service
    is viewed in my services it should also show that the cloud and
    machine credentials were attached to the service.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/2h
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
def test_default_view_settings_should_apply_for_service_catalogs():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1553337

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: Default view settings should apply for service catalogs
    """
    pass


@pytest.mark.manual
def test_default_reports_with_timelines_policy_events():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
def test_default_reports_with_timelines_vm_operation():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.timelines
@pytest.mark.tier(2)
def test_default_reports_with_timelines_vm_power_on_off_events_for_last_week():
    """
    Verify timeline events are rendered on Cloud Intelligence->Timelines

    Polarion:
        assignee: None
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/5h
    """
    pass


@pytest.mark.manual
@test_requirements.timelines
@pytest.mark.tier(2)
def test_default_reports_with_timelines_date_brought_under_management_for_last_week():
    """
    Verify timeline events are rendered on Cloud Intelligence->Timelines

    Polarion:
        assignee: None
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/5h
    """
    pass


@pytest.mark.manual
@test_requirements.timelines
@pytest.mark.tier(2)
def test_default_reports_with_timelines_policy_events_for_the_last_7_days():
    """
    Verify timeline events are rendered on Cloud Intelligence->Timelines

    Polarion:
        assignee: None
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/5h
    """
    pass


@pytest.mark.manual
@test_requirements.timelines
@pytest.mark.tier(2)
def test_default_reports_with_timelines_policy_events_for_last_week():
    """
    Verify timeline events are rendered on Cloud Intelligence->Timelines

    Polarion:
        assignee: None
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/5h
    """
    pass


@pytest.mark.manual
def test_default_reports_with_timelines_hosts():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
def test_default_reports_with_timelines_policy_events2():
    """
    None

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_user_cloud_cpu_quota_by_services():
    """
    test user cpu quota for cloud instance provision by ordering services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_zone_multiple_servers_server_setup():
    """
    using any type of depot check collect current log function under zone.
    Zone should have multiplie servers under it. Zone should not be setup,
    servers should

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_stack():
    """
    Stack CREATE
    Stack DELETE

    Polarion:
        assignee: mmojzis
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_custom_button_dialog_ssui():
    """
    Test custom button dialog runner via SSUI

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_custom_button_dialog_service_archived():
    """
    From Service OPS check if archive vms"s dialog invocation via custom
    button
    https://bugzilla.redhat.com/show_bug.cgi?id=1439883

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_running_processes():
    """
    Check running processes are fetched correctly for analysed VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_repos_available():
    """
    Repositories are included under Ansible, Check Empty State pattern is
    displayed when none exist.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(3)
def test_quota_for_simultaneous_service_catalog_request_with_different_users():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1456819

    Polarion:
        assignee: ghubale
        casecomponent: prov
        initialEstimate: 1/4h
        startsin: 5.8
        title: test quota for simultaneous service catalog request with different users
        testSteps:
            1.Create a service catalog with vm_name, instance_type &
              number_of_vms as fields. Set quotas threshold values for
              number_of_vms to 5. 2.Create two users from same group try
              to provision service catalog from different web-sessions
        expectedResults:
            1. Quota exceeded message should be displayed
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(2)
def test_ssui_test_snapshot_vm_memory_checkbox_when_creating_snapshot_for_powered_off_vm():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1600043

    Polarion:
        assignee: apagac
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/4h
        title: [SSUI] Test "snapshot vm memory" checkbox when creating
               snapshot for powered off vm.
        testSteps:
            1. test creating snapshot for powered off vm"s
        expectedResults:
            1. "snapshot vm memory" checkbox should not be displayed.
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_heat_stacks_in_non_admin_tenants_shall_also_be_collected():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1290005

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Heat stacks in non-admin tenants shall also be  collected
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_schedule_crud():
    """
    Create the automate task schedule and make sure all the values are the
    same after creation.
    Bug 1479570 - Internal Server Error when creating schedule for
    automate task
    https://bugzilla.redhat.com/show_bug.cgi?id=1479570
    1.) Create a schedule, selecting Automation Tasks under Action.
    2.) Select a value from the dropdown list under Object Attribute Type.
    3.) Undo the selection by selecting "<Choose>" from the dropdown.
    4.) No pop-up window with Internal Server Error.

    Polarion:
        assignee: tpapaioa
        casecomponent: automate
        initialEstimate: 1/15h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_vmware_credentials():
    """
    Allow user/admin to create/import credentials for machines which will
    be managed (may need to be split into multiple tests to cover
    -Machine, Network, Amazon Web Services, Rackspace, VMware vCenter, Red
    Hat Satellite 6, Red Hat CloudForms, Google Compute Engine, Microsoft
    Azure Classic, Microsoft Azure Resource Manager, OpenStack)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_add_to_shopping_cart_button_should_enable_after_refresh_on_some_dialog_fields_in_sui():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1539871

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        initialEstimate: 1/6h
        startsin: 5.10
        title: "Add to shopping cart" button should enable after refresh on
               some dialog fields in SUI.
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_repo_details():
    """
    test clicking on a repo name should show details of the repository.
    (Automation-Ansible-repositories table view showing added repos)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_web_services():
    """
    Web Services (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_validate_lookup_button_provsioning():
    """
    configure ldap and validate for lookup button in provisioning form

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_role_configuration_work_as_expected_for_new_ldap_groups():
    """
    Retrieve ldap user groups, assign roles to the group.
    Login to cfme webui as ldap user and verify user role is working as
    expected.
    NOTE: execute rbac test cases.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1h
        title: verify role configuration work as expected for new ldap groups
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_dialog_fields_should_update_after_hitting_save_in_dialog_editor():
    """
    de

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        title: Dialog fields should update after hitting save in dialog editor
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tag_expression_and_with_or_with_not():
    """
    Combine tags with AND and NOT and OR conditions
    Check item visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_vpc_env_selection():
    """
    Test selection of components in environment page of cloud instances
    with and without selected virtual private cloud
    Related to BZ 1315945

    Polarion:
        assignee: None
        casecomponent: web_ui
        initialEstimate: 1d
        testSteps:
            1. Provision an Azure Instance from an Image.
            2. At the environment page, try to select components without vpc
            3. At the environment page, try to select components without vpc with vpc
        expectedResults:
            1. Instance provisioned and added successfully
            2. Items are selected successfully
            3. Items are selected successfully
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_for_base_report_one_time_a_day():
    """
    Create schedule that runs report daily. Check it was ran successfully

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_passwords_are_not_registered_in_plain_text_in_auth_logs():
    """
    verify passwords are not registered in plain text in auth logs.
    1. Configure LDAP/External Auth/Database Auth.
    2. Verify username and passwords are not registered in plain text to
    audit.log and evm.log

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        title: verify passwords are not registered in plain text in auth logs.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_set_retirement_date_scvmm():
    """
    Verify that the retirement of a vm can be set in the future and that
    it actually gets retired.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_add_provider_without_subscription_azure():
    """
    1.Add Azure Provider w/0 subscription
    2.Validate

    Polarion:
        assignee: None
        casecomponent: cloud
        caseposneg: negative
        initialEstimate: 1/10h
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
        casecomponent: candu
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
@test_requirements.report
def test_report_menus_moving_reports():
    """
    Go to Cloud Intel -> Reports -> Edit reports menuSelect EvmGroup
    Administrator -> Configuration Management -> Virtual MachinesSelect
    Virtual Machines folder
    Select 5 Reports and move them to the left.
    All 5 reports should be moved.
    Then reset it and select all reports and move them to the left.
    All reports should be moved.

    Polarion:
        assignee: anikifor
        casecomponent: report
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_it_should_add_new_service_catalog_item_when_display_in_catalog_selected_and_no_catalo():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1630385

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: None
        startsin: 5.9
        title: It should add new Service Catalog Item when "Display in
               Catalog" selected and no Catalog chosen
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
@pytest.mark.tier(1)
def test_proxy_override_gce():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the ec2 proxy settings.  For this test you want to create a
    bogus setting for the default entry and a correct entry for ec2 so
    that you can make sure it is switching to ec2 correctly.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
        setup: Make sure you create a bad proxy for default and a correct proxy for
               ec2 so that you are certain we grab the right entry.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_override_ec2():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the ec2 proxy settings.  For this test you want to create a
    bogus setting for the default entry and a correct entry for ec2 so
    that you can make sure it is switching to ec2 correctly.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
        setup: Make sure you create a bad proxy for default and a correct proxy for
               ec2 so that you are certain we grab the right entry.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_override_azure():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  For this test you want to create a
    bogus setting for the default entry and a correct entry for azure so
    that you can make sure it is switch to azure correctly.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/4h
        setup: Setup the azure proxy correct and the default proxy incorrectly and
               make sure azure uses the correct entry.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_rbac_user_with_no_permissions_should_not_be_able_to_create_catalog_item():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1460891

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: RBAC : User with no permissions should not be able to create catalog item
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_zone_credentials_windows():
    """
    This test verified that the Windows credential can be set and that
    these credentials allow CFME to connect to a Windows VM.  Used for
    Collect Running Processes.

    Polarion:
        assignee: None
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        upstream: yes
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
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_able_to_add_long_description_for_playbook_catalog_items():
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Able to add long description for playbook catalog items
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_containers_topology_display_names():
    """
    Navigate to Compute -> Containers -> Topology.Check whether the
    "Display Name" box is displayed correctly.

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: low
        initialEstimate: 1/30h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_utilization_cluster():
    """
    Verify гutilication data from cluster

    Polarion:
        assignee: None
        casecomponent: optimize
        caseimportance: medium
        initialEstimate: 1/8h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_ldap_user_login():
    """
    Verify the user login with valid credentials, based on role configured
    for the user.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        testSteps:
            1. login with the valid ldap user configured with CFME
            2. Verify the logged in user details in login page
            3. verify the feature access for the user based on the role
               configured/assigned to the user.
            4. verify the login with invalid credentials for the user login
        expectedResults:
            1. Login is expected to be successful for the valid user and credentials.
            2. username and group name needs be displayed.
            3. the user is expected to get full access to the features defined for his role.
            4. Login is expected to fail with invalid credentials.
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenant_unique_automation_domain_name_on_parent_level():
    """
    Automation domain name is unique across parent tenants and cannot be
    used twice.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.5
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
        casecomponent: cloud
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
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: Add Cloud Key pair
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_textbox_value_should_update_with_automate_method():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1613443

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: TextBox value should update with automate method
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
@test_requirements.ansible
@pytest.mark.tier(3)
def test_custom_button_order_ansible_playbook_service():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1449361 An Ansible Service
    Playbook can be ordered from a Custom Button

    Polarion:
        assignee: sbulage
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_vds_deploy_target():
    """
    Target vDS for deployment

    Polarion:
        assignee: None
        casecomponent: infra
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_cluster():
    """
    Verify bottleneck events from cluster

    Polarion:
        assignee: None
        casecomponent: optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_copy_generate_report_provisioning_activity():
    """
    1.Copied the report "Provisioning Activity - by Requester" to
    "Provisioning Activity - by Requester-2"
    2.Executing the copied report, one can se the vaule "Administrator"
    for the field "Provision.Request : Approved By".
    If one later configures the Styling to:
    Style: if: Red Background = Administrador Light Background Starts With
    A
    https://bugzilla.redhat.com/show_bug.cgi?id=1402547

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1348625
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
        casecomponent: appl
        initialEstimate: 1/4h
        startsin: 5.8
        title: Verify purging of old records
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_configuration_management_ansible_tower_job_templates():
    """
    Combination of My Company tag and ansible tower job template

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_configuration_icons_trusted_forest_settings():
    """
    Go to Configuration -> Authentication
    Select Mode LDAP
    Check Get User Groups from LDAP
    Now there should be green plus icon in Trusted Forest Settings

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/20h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_vm_collect_running_processes():
    """
    Verify that you can extract the running processes from a VM with a
    Windows Guest OS that is running and has an IP Address.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
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
        casecomponent: prov
        initialEstimate: 1h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_gce_credentials():
    """
    Add GCE credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_when_clicking_refresh_for_text_field_2_only_text_field_2_should_refreshed_of_service_():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1559999
    Steps to Reproduce:
    1. create a dialog with two text fields with no refresh relation
    between them, showing their refresh buttons.
    2. associate each to a different method that just logs "Refreshing X"
    3. associating the dialog to a catalog item
    4. tail -f log/automation.log | grep "Refreshing"
    5. load the dialog
    6. click "refresh" for field 2

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: When clicking refresh for text field 2 only text field 2
               should refreshed of service dialog
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_disable_local_login_option_works_fine_verify_enable_disable_option():
    """
    Configure external auth as in TC#1 and enable “disable local login.”
    Verify the default “admin” user for cfme no longer allowed to login to
    CFME
    ‘"disable local login". can be reset with an administratively
    privileged user and using the appliance_console "Update Ext Auth"
    option.
    Verify “admin” login works fine upon “disable local login” is
    disabled.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: Verify disable local login option works fine. Verify enable/disable option
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_dialogs_including_a_tag_control_element_should_submit_the_dialog():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1569470
    1. create a dialog with a tag control element
    2. configure the tag control element to be required
    3. associated the dialog with a service
    4. log into self-service to load the dialog
    5. Submit the dialog

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Dialogs including a tag control element should submit the dialog
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
        casecomponent: prov
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
        assignee: None
        casecomponent: cloud
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
    Relevant BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1563241

    Polarion:
        assignee: apagac
        casecomponent: control
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
@test_requirements.service
@pytest.mark.tier(2)
def test_reconfigure_service_for_dialogs_with_timeout_values():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1442920

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/4h
        title: Test reconfigure service for dialogs with timeout values
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenantadmin_user_crud():
    """
    As a Tenant Admin I want to be able to create users in my tenant
    1. Login as super admin and create new tenant
    2. Create new role by copying EvmRole-tenant_administrator
    3. Create new group and choose role created in previous step and your
    tenant
    4. Create new tenant admin user and assign him into group created in
    previous step
    5. login as tenant admin
    6. Perform crud operations
    Note: BZ 1278484 - tenant admin role has no permissions to create new
    roles - Workaround is to add modify permissions to
    tenant_administrator role or Roles must be created by
    superadministrator
    5.5.0.13 - after giving additional permissions to tenant_admin - able
    to create new roles

    Polarion:
        assignee: mnadeem
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1608554
    1. Login with user with Services > My Services > Requests > Operate
    enabled
    2. View Services > Requests
    3. Query API on service_requests

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        tags: rbac
        title: Test requests in UI and API
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_childtenant_cloud_cpu_quota_by_enforce():
    """
    test cpu quota for child tenant for cloud instance by enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
def test_crud_pod_appliance_ext_db():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance

    Polarion:
        assignee: izapolsk
        initialEstimate: None
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
        casecomponent: cloud
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_check_quota_regression():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1554989
    Update from 5.8.2 to 5.8.3 has broken custom automate method.  Error
    is thrown for the check_quota instance method for an undefined method
    provisioned_storage.
    You"ll need to create an invalid VM provisioning request to reproduce
    this issue.
    The starting point is an appliance with a provider configured, that
    can successfully provision a VM using lifecycle provisioning.
    1. Add a second provider to use for VM lifecycle provisioning.
    2. Add a 2nd zone called "test_zone". (Don"t add a second appliance
    for this zone)
    3. Set the zone of the second provider to be "test_zone".
    4. Provision a VM for the second provider, using VM lifecycle
    provisioning. (The provisioning request should remain in
    pending/active status and should not get processed because there is no
    appliance/workers for the "test_zone".)
    5. Delete the template used in step 4.(Through the UI when you
    navigate to virtual machines, templates is on the left nav bar, select
    the template used in step 4 and select: "Remove from Inventory"
    6. Provisioning a VM for the first provider, using VM lifecycle
    provisioning should produce the reported error.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_pod_appliance_db_upgrade():
    """
    db scheme/version has been changed

    Polarion:
        assignee: izapolsk
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_against_openstack():
    """
    Execute playbook against Openstack provider.
    Workaround must be applied:
    https://bugzilla.redhat.com/show_bug.cgi?id=1511017

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: appl
        caseimportance: critical
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Users are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Users  are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu Instance.
    3. Check Users are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_rhos7_ga_fedora_22_ext4():
    """
    test_ssa_users[rhos7-ga-fedora-22-ext4]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Users are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_users_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_cloud_icons_instances():
    """
    Requirement: Have a cloud provider added.Navigate to Compute -> Cloud
    -> Instances
    Mark off any instance.
    Go through all select bars and everything on this page and check for
    missing icons.

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/20h
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
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
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_set_ownership_back_to_default():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1483512

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        title: Set Ownership back to default
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_after_setting_certain_types_of_filters_filter_tab_should_be_accessible_and_editable():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1519809
    Steps to Reproduce:
    1.configure a report using a filter based on "EVM Custom Attributes:
    Name" and "EVM Custom Attributes: Value"
    2.
    3.
    Actual results:
    after saving changes, trying to edit the filter will result in the
    user looping and being unable to access the page. Attempts to access
    the report will also cause puma to consume all cpu on at least one
    thread

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/4h
        title: After setting certain types of filters filter tab should be
               accessible and editable
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
def test_can_only_select_this_regions_zones_when_changing_server_zone():
    """
    Bug 1470283 - zones of sub region show up as zones appliances of a
    central region can move to
    https://bugzilla.redhat.com/show_bug.cgi?id=1470283
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
        assignee: anikifor
        casecomponent: config
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


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_overridden_extra_vars():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1444107Once a Ansible
    Playbook Service Dialog is built, it has default parameters, which can
    be overridden at "ordering" time. Check if the overridden parameters
    are passed.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_add_public_repo():
    """
    Ability to add public repo (without SCM credentials).

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_disable_toast_notifications_by_role_in_sui():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1496233

    Polarion:
        assignee: nansari
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: Disable toast notifications by role in SUI
    """
    pass


@pytest.mark.manual
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
        casecomponent: cloud
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_verify_ldap_user_login_when_email_has_an_apostrophe_character():
    """
    refer the BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1379420

    Polarion:
        assignee: apagac
        caseimportance: low
        initialEstimate: 1/3h
        title: verify ldap user login when email has an apostrophe character
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_user_quota_via_ssui():
    """
    Create user quota
    assign some quota limitations
    try to provision over limit via ssui

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenant_automation_domains():
    """
    Tenants can see Automation domains owned by tenant or parent tenants
    1) Configure LDAP authentication on CFME
    2) Create 2 different parent parent-tenants
    - marketing
    - finance
    2) Create groups marketing and finance (these are defined in LDAP) and
    group names in LDAP and CFME must match
    Assign these groups to corresponding tenants and assign them EvmRole-
    SuperAdministrator roles
    3) In LDAP we have 3 users:
    - bill -> member of marketing group
    - jim -> member of finance group
    - mike -> is member of both groups
    4) In each tenant create new Automation domain and copy
    ManageIQ/System/Request/InspectMe instance and
    ManageIQ/System/Request/new_method method to new domain
    5) User can see only domains (locked) from his parent tenants and can
    create his own which are visible only to his tenant

    Polarion:
        assignee: mnadeem
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_domain_import_with_no_connection():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1391208

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_send_report():
    """
    Create schedule
    Send an E-mail" and add more than five users in the mailing list.
    Un-check "Send if Report is Empty" option and select the type of
    attachmentQueue up this Schedule

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.cloud_init
@pytest.mark.tier(1)
def test_cloud_init_cfme():
    """
    test adding cloud init payload to cfme appliance (infra-PXE clod init)

    Polarion:
        assignee: None
        casecomponent: appl
        endsin: 5.4
        initialEstimate: 1/2h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_schema_field_without_type():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1365442
    It shouldn"t be possible to add a field without specifying a type.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Packages.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_rhos7_ga_fedora_22_ext4():
    """
    test_ssa_packages[rhos7-ga-fedora-22-ext4]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Packages.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Packages.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu Instance.
    3. Check Packages are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Applications are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Packages are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Packages are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_packages_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_ldap_authentication_works_without_groups_from_ldap_by_uncheck_the_get_user_gro():
    """
    verify LDAP authentication works without groups from LDAP
    refer this bz: https://bugzilla.redhat.com/show_bug.cgi?id=1302345
    Steps:
    1.In Configuration->Authentication, set the auth mode to LDAP.
    LDAP Hostname: "cfme-openldap-rhel7.cfme.lab.eng.rdu2.redhat.com"
    LDAP Port: 389
    UserType: Distinguished Name (UID=<user>)
    User Suffix: UID=<user> :  ou=people,ou=prod,dc=psavrocks,dc=com
    2. uncheck the "Get User Groups from LDAP"
    3. In Access Control -> Users, created new user
    "uid=test,ou=people,ou=prod,dc=psavrocks,dc=com" and set Group to
    EvmGroup-administrator
    ("uid=test,ou=people,ou=prod,dc=psavrocks,dc=com" user is already
    created in LDAP Server)
    4. Logout and tried Login with username: test and password: test,
    Login failed.
    Expected results:
    Base DN should always be visible and should be part of the LDAP
    Settings, when it is always needed.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/4h
        title: verify LDAP authentication works without groups from LDAP by
               uncheck the "Get User Groups from LDAP"
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_ansible_tower_tag_configured_system():
    """
    "Setup: Create group with tag, use this group for user creation
    1. Add tag(used in group) for Ansible Tower configured_system via
    detail page
    2. Remove tag for Ansible Tower configured_system via detail page
    3. Add tag for Ansible Tower configured_system via list
    4. Check Ansible Tower configured_system is visible for restricted
    user
    5. Remove tag for Ansible Tower configured_system via list
    6 . Check ansible tower configured_system isn"t visible for restricted
    user"

    Polarion:
        assignee: anikifor
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_vds_ui_display():
    """
    Virtual Distributed Switch port groups are displayed for VMs assigned
    to vds port groups.
    Compute > Infrastructure > Host > [Select host] > Properties > Network

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_verify_login_fails_for_user_in_cfme_after_changing_the_password_in_saml_for_the_user():
    """
    Configure SAML for cfme.
    Create user and assign group in saml.
    Create groups in cfme, and login and SAML user.
    Logout
    Change user credentials in SAML server.
    Verify user login  to CFME using old credential fails.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        title: Verify login fails for user in CFME after changing the
               Password in SAML for the user.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_retry_onexit_increases():
    """
    To reproduce:
    1) Import the attached file, it will create a domain called
    OnExitRetry
    2) Enable the domain
    3) Go to Automate / Simulation
    4) Simulate Request with instance OnExitRetry, execute methods
    5) Click submit, open the tree on right and expand ae_state_retries
    It should be 1 by now and subsequent clicks on Retry should raise the
    number if it works properly.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_invalid_azure():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  You just need to fill in the
    appropriate information, only screw up a few of the values to make
    sure it reports a connection error.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/2h
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_invalid_gce():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  You just need to fill in the
    appropriate information, only screw up a few of the values to make
    sure it reports a connection error.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        setup: The only thing different you need to do for this is enter some wrong
               information and Refresh Relationships.  Wait two minutes and refresh
               the page.  You"ll definitely get an error if any of the values are
               wrong.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_invalid_default():
    """
    With 5.7 there is a new feature that allows users to specify a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the default proxy settings.  You just need to fill in the
    appropriate information, only screw up a few of the values to make
    sure it reports a connection error.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/2h
        setup: The mojo page has all the information you will need.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_invalid_ec2():
    """
    With 5.7 there is a new feature that allows users to specify a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the ec2 proxy settings.  You just need to fill in the
    appropriate information, only screw up a few of the values to make
    sure it reports a connection error.
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
        setup: Follow the instructions in the mojo document.
        startsin: 5.7
        teardown: You should probably reset or delete the changes.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_host_combination():
    """
    Combine My Company tag tab restriction, with Clusters&Host tab
    Visible host should match both tab restrictions

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_server_zone_setup():
    """
    using any type of depot check collect current log function under
    appliance (settings under server should not be configured, under zone
    should be configured)

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_server_server_setup():
    """
    using any type of depot check collect current log function under
    appliance (settings under applince should be configured, under zone
    should not be configured)

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
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
@pytest.mark.tier(1)
def test_proxy_valid_gce():
    """
    With 5.7.1 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  You just need to fill in the
    appropriate information
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/4h
        setup: Configure advanced settings for GCE proxy.
               Add gce provider
               Probably need to check the packets to make sure they are vectoring
               through the proxy server, or just check the proxy server log.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_valid_default():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  You just need to fill in the
    appropriate information
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/2h
        setup: Follow the instructions in the mojo doc above.
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_valid_azure():
    """
    With 5.7 there is a new feature that allows users to specific a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the azure proxy settings.  You just need to fill in the
    appropriate information
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/2h
        setup: Configure advanced settings for Azure proxy.
               Add azure provider
               Probably need to check the packets to make sure they are vectoring
               through the proxy server, or just check the proxy server log.
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_proxy_valid_ec2():
    """
    With 5.7 there is a new feature that allows users to specify a
    specific set of proxy settings for each cloud provider.  The way you
    enable this is to go to Configuration/Advanced Settings and scroll
    down to the ec2 proxy settings.  You just need to fill in the
    appropriate information
    Here are the proxy instructions:
    https://mojo.redhat.com/docs/DOC-1103999

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/2h
        setup: Follow the instructions in the mojo doc above as it is easier to
               change in one place.
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_simulation_result_has_hash_data():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1445089
    The UI should display the result objects if the Simulation Result has
    hash data.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_two_factor_authentication_works_with_user_password_and_otp():
    """
    Verifies two factor auth using external_authentication:
    Steps:
    1. configure CFME for external auth (IPA, SAML etc..)
    2. configure user for OTP in authentication server.
    3. verify two factor authentication for CFME works with user password
    and otp.

    Polarion:
        assignee: apagac
        initialEstimate: 1/3h
        title: verify two factor authentication works with user password and otp.
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_amazon_credentials():
    """
    Add Amazon credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_timepicker_should_pass_correct_timing_on_service_order():
    """
    Timepicker doesn"t pass correct timing on service order

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Timepicker should pass correct timing on service order
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_should_be_able_to_see_requests_if_our_users_are_in_groups_with_managed_tags():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1596738
    rootTenant
    |
    subTenant
    /           |               \
    sub2Tenant sub2Tenant2 sub2Tenant3
    usiness_group, can be: team1, team2, team3
    business_unit, can be: fr, de, uk
    We have 3 user groups:
    groupA, attached to rootTenant and no filter, custom role full access
    groupB, attached to rootTenant and filter business_unit=fr, custom
    role access to catalog, services and machines
    groupC, attached to sub2Tenant and filter business_unit=fr &
    business_group=teamC, custom role access to catalog, services and
    machines (same as for groupB)

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        title: Should be able to see requests if our users are in groups with managed tags
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_ldap_user_group():
    """
    verifies the ldap user group by loggin with different users across
    groups.
    setup/pre-requisite: configure the ldap with multiple groups and users
    defined in each group

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        testSteps:
            1.configure CFME appliance with ldap authentication mode.
            2. configure Access Control for multiple groups/users defined in the ldap
            3. login with users in different groups, with valid credentials
            4. verify the user logged in has no access to the user
               details/data defined in other groups
        expectedResults:
            1. ldap configuration should be successful.
            2. CFME configuration for multiple users/groups should work without any error.
            3. login should be successful upon valid credentials input.
            4. user should have access to only the data defined by him/group
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_import_without_master():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1508881
    Git repository doesn"t have to have master branch

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_edit_catalog_item_after_remove_resource_pool():
    """
    Create catalog item with a resource pool , Remove resource pool from
    the provider and then edit catalog item.

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.5
        testSteps:
            1. Create a catalog item
            2. Select cluster and resource pool and Save
            3. Remove resource pool from provider
            4. Edit catalog
        expectedResults:
            1.
            2.
            3.
            4. Validation message should be shown
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_optimize_memory_usage_by_making_object_in_hash():
    """
    The object in the hash reference should be as small as possible,
    so we don"t need to store that many data in memory.

    Polarion:
        assignee: None
        casecomponent: appl
        initialEstimate: 1h
        title: Optimize memory usage by making object in hash
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_key_pairs_quadicon():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1352914
    Requirement: Have a cloud provider with at least one key pair
    1. Go to Compute -> Cloud -> Key Pairs
    2. Set View to Grid
    3. Cloud with two keys icon should be displayed(auth_key_pair.png)
    4. Same in Key Pairs summary.

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/20h
    """
    pass


@pytest.mark.manual
def test_default_views_can_save_or_reset():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1389225
    1) Go to My Settings -> Default views
    2) Change something and try to reset configuration
    3) Change something and try to save it

    Polarion:
        assignee: pvala
        casecomponent: config
        initialEstimate: 1/20h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_disabling_dashboard_under_service_ui_for_a_role_shall_disable_the_dashboard():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1589409

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Disabling "Dashboard" under service UI for a role shall disable the dashboard
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
        casecomponent: cloud
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1535556
    1. disable "manage quota" from the role of a user
    2. try to view quotas as that user
    copy the EVMRole-tenant_quota_administrator role, disable Settings ->
    Configuration -> Access Control -> Tenants -> Modify -> Manage Quotas
    and still view quotas when the "Manage Quotas" button was no longer
    available.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: None
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
        casecomponent: cloud
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.drift
@pytest.mark.tier(1)
def test_drift_analysis_vpshere6_rhel():
    """
    1. Go to Compute-> Infrastructure-> Virtual Machines -> Select any vm
    for SSA
    2. Perform SSA on VM
    3. Next, Reconfigure the VM with change in memory and CPU etc.
    4. Again perform SSA on VM
    5. Next, compare drift history
    6. Check the drift comparison
    Validate that updated values get displayed.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.3
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
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_project_cloud_memory_quota_by_enforce():
    """
    test memory quota for project for cloud instance by enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        setup: Prerequisities:
               * A provider set up, supporting provisioning in CFME
        startsin: 5.5
        testSteps:
            1. Set the project tenant quota for cpu by UI enforcement
            2. Open the provisioning dialog.
            3. Apart from the usual provisioning settings, set memory
               greater then tenant quota memory
            4. Submit the provisioning request and wait for it to finish.
            5. Visit the requests page. The last message should state quota validation message
        expectedResults:
            1.
            2.
            3.
            4.
            5.
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_provider_refresh_via_api():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1602413
    1. set up a new user with a new group based on vm_user plus api access
    and refresh access to cloud and infrastructure providers
    2. issue a refresh using the classic ui with that user
    3. issue a refresh of the same provider using the api

    Polarion:
        assignee: apagac
        casecomponent: infra
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
        assignee: mkourim
        caseimportance: medium
        initialEstimate: None
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.discovery
@pytest.mark.tier(1)
def test_infrastructure_providers_rhevm_edit_provider_no_default_port():
    """
    1) Add a rhevm provider
    2) Edit it and try to change it to another rhevm provider
    3) There shouldn"t be any default API port and API port should be
    blank

    Polarion:
        assignee: pvala
        casecomponent: infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.c_and_u
@pytest.mark.tier(2)
def test_utilization_host():
    """
    Verify гutilication data from host

    Polarion:
        assignee: None
        casecomponent: optimize
        caseimportance: medium
        initialEstimate: 1/8h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_state_machine_variable():
    """
    Test whether storing the state machine variable works and the vaule is
    available in another state.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
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
        casecomponent: appl
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_value_input_into_service_dialog_element():
    """
    A value input into a service dialog element is not always visible to
    another dynamic element that is set to auto refresh
    https://bugzilla.redhat.com/show_bug.cgi?id=1364407

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: test value input into service dialog element
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
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_ui_requests_notifications():
    """
    After all processes are running and websockets role is enabled, add a
    new repo to embedded tower and check the notifications display
    correctly. With a Green banner to show it was successful.
    https://bugzilla.redhat.com/show_bug.cgi?id=1471868

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/6h
        startsin: 5.8
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_hw_hot_vsphere67_nested_cores_per_socket():
    """
    test changing vm"s cpu cores

    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        setup: -get new configured appliance
               -add vmware provider
               -provision new vm
               -select vm
               -configure-->reconfigure vm
               -increase/decrease the cpu cores
               -check changes
        startsin: 5.5
        testSteps:
            1. Increase vm cpu cores
            2. Decrease vm cpu cores
        expectedResults:
            1. Changes shouldn"t succeed
            2. Changes shouldn"t succeed
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_hw_hot_vsphere67_nested_sockets():
    """
    test change vm"s cpu sockets

    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        setup: -get new configured appliance
               -add vmware provider
               -provision new vm
               -select vm
               -configure-->reconfigure vm
               -increase/decreasing cpu sockets
               -check changes
        startsin: 5.5
        testSteps:
            1. Increase sockets of vm
            2. Decrease sockets of vm
        expectedResults:
            1. Changes should succeed
            2. Changes shouldn"t succeed
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_hw_hot_vsphere67_nested_memory():
    """
    test changing the memory of a vm

    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        setup: -get new configured appliance
               -add vmware provider
               -provision new vm
               -select vm
               -configure-->reconfigure vm
               -increase/decrease the memory and submit
               -check changes
        startsin: 5.5
        testSteps:
            1. Increase memory of selected VM
            2. Decrease memory of select vm
        expectedResults:
            1. Changes should succeed
            2. Changes should fail (you can"t hot decrease memory) [Error:
               The operation is not supported on the object.]
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_manual_placemant_cluster_only():
    """
    VMware MANUAL Placement to Support ONLY Clusters

    Polarion:
        assignee: None
        casecomponent: infra
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_api_auth():
    """
    The Tower API should not be wide open, authentication is required.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_service_retirement_requests_shall_be_run_by_the_user():
    """
    Create a request from non-admin user. Request shall be run by user.

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: service retirement requests shall be run by the user
    """
    pass


@pytest.mark.manual
@test_requirements.settings
@pytest.mark.tier(3)
def test_validate_landing_pages_for_rbac():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1450012

    Polarion:
        assignee: pvala
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/5h
        title: test validate landing pages for rbac
        testSteps:
            1.create a new role by selecting few product features.
              2.create a group base on the above role and the create a new
              user with this group 3.Login with the new user and navigate
              to my settings->visuals and check the start page entries in
              show at login drop down list
        expectedResults:
            1. Display landing pages for which the user has access to
    """
    pass


@pytest.mark.manual
@test_requirements.discovery
def test_add_infra_provider_screen():
    """
    Manually add provider using Add screen
    Provider Add:
    -test form validation using incorrect format for each field
    -test wrong ip
    -test wrong credentials
    -test verify cretentials
    -test verify wrong credentials
    -test wrong security protocol
    -test wrong provider type

    Polarion:
        assignee: pvala
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_vm_combination():
    """
    Combine My Company tag restriction tab with VM&Tepmlates restriction
    tab
    Vm , template should match both tab restrictions

    Polarion:
        assignee: anikifor
        casecomponent: config
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
@test_requirements.ansible
def test_embed_tower_exec_play_against_gce():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against Google Compute Engine Cloud with GCE
    credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_zone_zone_multiple_servers_server_setup():
    """
    using any type of depot check collect all log function under zone.
    Zone should have multiplie servers under it. Zone should not be setup,
    servers should

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_new_dialog_editor_entry_point_should_be_mandatory_for_dynamic_elements():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1488579

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        startsin: 5.9
        title: New dialog editor : Entry point should be mandatory for dynamic elements
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_template_info_scvmm():
    """
    The purpose of this test is to verify that the same number of
    templates in scvmm are in cfme.  Take the time to spot check a random
    template and check that the details correspond to SCVMM details.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_snapshot_tree_view_functionality():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1398239
    Just test the snapshot tree view. Create a bunch of snapshots and see
    if the snapshot tree seems right. Check if the last created snapshot
    is active. Revert to some snapshot, then create another bunch of
    snapshots and check if the tree is correct.

    Polarion:
        assignee: apagac
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/4h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1398239
        title: Test snapshot tree view functionality
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_superadmin_child_tenant_delete_parent_catalog():
    """
    Child superadmin tenant should able to delete catalog belonging to
    superadmin in parent tenant. This is by design tenancy has not been
    split any further and at this point is not expected to be changed
    Note: As per below BZ#1375713,  Child superadmin tenant should not
    delete catalog belonging to superadmin in parent tenant. However as
    per the current code base this is by design: "ServiceTemplate"
    => :ancestor_ids,
    https://github.com/ManageIQ/manageiq/blob/2a66cb59e26816c7296896620b5b
    7731b350943d/lib/rbac/filterer.rb#L114
    You"re able to see Catalog items of parent and ancestor tenants.  If
    your role has permission to modify catalog items / delete them, and
    you can to see ones from ancestor tenants, then you can delete them.
    https://bugzilla.redhat.com/show_bug.cgi?id=1375713

    Polarion:
        assignee: mnadeem
        casecomponent: config
        initialEstimate: 1/2h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(3)
def test_report_fullscreen_enabled():
    """
    Navigate to Intelligence > Reports
    (queue same report twice)
    1)Sucesful report generting [populated]
    Select Generating Report
    -check Configuration > Show Fullscreen Report is disabled
    Wait ~1minute and Select sucesfully generated report
    -check Configuration > Show Fullscreen Report is enabled
    Select Show Fullscreen Report
    -check report was shown in fullscreen
    2)Select report with no data for reporting, queue the report [blank]
    (queue same report twice)
    Select Generating Report
    -check Configuration > Show Fullscreen Report is disabled
    Wait ~1minute and Select sucesfully generated report
    -check Configuration > Show Fullscreen Report is disabled
    Navigate to Intelligence > Saved Reports
    3)Select group of [populated] reports
    In table, select one of reports
    -check Configuration > Show Fullscreen Report is enabled
    Select Show Fullscreen Report
    -check report was shown in fullscreen
    Select both of reports
    -check Configuration > Show Fullscreen Report is disabled
    4)Select group of [blank] reports
    In table, select one of reports
    -check Configuration > Show Fullscreen Report is disabled
    Select both of reports
    -check Configuration > Show Fullscreen Report is disabled

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provider_summary_scvmm2016():
    """
    The purpose of this test is to verify that the information on the
    provider summary is substantially the same as what is on SCVMM.
    Since SCVMM-2016 only has a short sequence of test cases, you must use
    this test case as the catch all to go in and spend 15-30 minutes and
    check as many links from this page and verify both the navigation and
    the content.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provider_summary_scvmm():
    """
    The purpose of this test is to verify that the information on the
    provider summary is substantially the same as what is on SCVMM.
    Since SCVMM-SP1 only has a short sequence of test cases, you must use
    this test case as the catch all to go in and spend 15-30 minutes and
    check as many links from this page and verify both the navigation and
    the content.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tagvis_host_change():
    """
    Enable / Disable a host in the group and check its visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vm_relationship_datastore_fileshare_scvmm():
    """
    Valid for SCVMM with Host which have Fileshare storage
    1.Provision Vm into fileshare linked to the host
    2.Check VM"s relationships - Datastore

    Polarion:
        assignee: ghubale
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(1)
def test_verify_groups_for_tenant_user():
    """
    verify if only 1 group displayed when login as tenant user ()that one
    where user belongs to)

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tagvis_provision_fields():
    """
    1. Create restricted user
    2. Check items restrictions for provision fields
    3. Check items restriction for fields while service order

    Polarion:
        assignee: anikifor
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
def test_ec2_tags_mapping():
    """
    Requirement: Have an ec2 provider
    1) Create an instance and tag it with test:testing
    2) Go to Configuration -> CFME Region -> Map Tags
    3) Add a tag:
    Entity: Instance (Amazon)
    Label: test
    Category: Testing
    4) Refresh provider
    5) Go to summary of that instance
    6) In Smart Management field should be:
    My Company Tags testing: Testing
    7) Delete that instance

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(2)
def test_instance_quota_reconfigure_with_flavors():
    """
    Test reconfiguration of instance using flavors after setting quota

    Polarion:
        assignee: ghubale
        casecomponent: cloud
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(3)
def test_distributed_zone_create_new():
    """
    Create new zone in local region

    Polarion:
        assignee: tpapaioa
        casecomponent: config
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
@test_requirements.quota
@pytest.mark.tier(1)
def test_project_cloud_vm_quota_by_enforce():
    """
    test no of vms quota for project for cloud instance by enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_service_dialog_default_values_should_be_rendered_in_dialog_fields():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1385898
    Create a dialog .set default value
    Use the dialog in a catalog .
    Order catalog.
    Default values should be shown

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/8h
        title: Service Dialog : Default values should be rendered in dialog fields
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_service_dialog_elements_with_regex_validation_should_be_validated():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1518971
    Steps to Reproduce:
    1. Create a Service Dialog
    2. Add an element such as a text box and add a validation regex
    3. Create a Catalog Item using the previously created Service Dialog
    4. Order the Catalog Item
    5. Enter data that fails to validate against the regex

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Service Dialog Elements with regex validation should be validated
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
        casecomponent: services
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
@test_requirements.service
@pytest.mark.tier(3)
def test_child_dialog_should_update_with_new_options_based_on_option_of_parent_dialog_upon_ref():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1580535

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        title: Child dialog should update with new options based on option
               of parent dialog upon refreshing
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_notification_window_events_show_in_timestamp_order():
    """
    Bug 1469534 - The notification events are out of order
    https://bugzilla.redhat.com/show_bug.cgi?id=1469534
    If multiple event notifications are created near-simultaneously (e.g.,
    several VM"s are provisioned), then clicking on the bell icon in the
    top right of the web UI displays the event notifications in timestamp
    order.

    Polarion:
        assignee: tpapaioa
        casecomponent: web_ui
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
@test_requirements.service
@pytest.mark.tier(3)
def test_dynamic_dropdown_values_should_load_correctly():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1581996
    Steps to Reproduce:
    1. Import the dialog and domain attached .
    2. Select Contract A . Contract B gets selected .
    3. In Location no values are loaded .

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Dynamic dropdown Values should load correctly
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(2)
def test_ssa_with_snapshot_scvmm2():
    """
    Needed to verify this bug -
    https://bugzilla.redhat.com/show_bug.cgi?id=1376172
    There is a vm called LocalSSATest33 that is preconfigured for this
    test.
    I"ll do these one off tests for a while.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.6.1
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_quota_vm_reconfigure():
    """
    Steps:
    1)Copy Automation-->Automate-->Explorer-->ManageIQ-->system-->CommonMe
    thods-->QuotaStateMachine-->quota
    as Automation-->Automate-->Explorer-->quota_test-->system-->CommonMeth
    ods-->QuotaStateMachine-->quota
    2) Create a Vm with in the limits of quota defined
    3) Try to reconfigure the Vm with values above quota set in Automation
    -->Automate-->Explorer-->quota_test-->system-->CommonMethods-->QuotaSt
    ateMachine-->quota

    Polarion:
        assignee: ghubale
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.8
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
        casecomponent: control
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
    V2V Test for https://bugzilla.redhat.com/show_bug.cgi?id=1651352
    https://bugzilla.redhat.com/show_bug.cgi?id=1653412

    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        caseimportance: medium
        initialEstimate: None
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
        casecomponent: report
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1449020

    Polarion:
        assignee: sshveta
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/4h
        title: Show tag info for playbook services
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_hot_vsphere67_nested_independent_persistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_hot_vsphere67_nested_independent_persistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_hot_vsphere67_nested_persistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_storage_profile_vm_summary():
    """
    Correctly display the name of the storage profile

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_cluster_vm_combination():
    """
    Combine My Company tag, Cluster and VM/Template
    All restriction should be applied for vm and template

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_snapshot_link_in_vm_summary_page_after_deleting_snapshot():
    """
    test snapshot link in vm summary page after deleting snapshot
    Have a vm, create couple of snapshots. Delete one snapshot. From the
    vm summary page use the history button and try to go back to
    snapshots. Go to the vm summary page again and try to click snapshots
    link, it should work.

    Polarion:
        assignee: apagac
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/6h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1395116
        title: test snapshot link in vm summary page after deleting snapshot
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_coordinator_singleton():
    """
    C & U Coordinator (singleton role)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
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
        assignee: None
        casecomponent: cloud
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
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_rbac_see_catalogs_and_orders_as_user_with_permissions():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1438922

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : RBAC : see catalogs and orders as user with permissions
    """
    pass


@pytest.mark.manual
def test_pod_appliance_db_backup_restore():
    """
    database has been saved and recovered

    Polarion:
        assignee: izapolsk
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_dialog_dropdown_ui_values_in_the_dropdown_should_be_visible_in_edit_mode():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1557508

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        title: Dialog dropdown UI values in the dropdown should be visible in edit mode
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_embed_tower_credentials():
    """
    Credentials included under ansible shown in a table view (automation-
    ansible-credentials)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/12h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_cockpit_after_uninstalling():
    """
    Test if cockpit is working after uninstalling from the VM (negative
    test)

    Polarion:
        assignee: sshveta
        casecomponent: infra
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
        title: Test Cockpit after uninstalling
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_topology_status():
    """
    Polarion:
        assignee: None
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/12h
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
@pytest.mark.tier(2)
def test_automate_method_copy():
    """
    Should copy selected automate method/Instance without going into edit
    mode.
    Steps:
    1. Add new domain (In enabled/unlock mode)
    2. Add namespace in that domain
    3. Add class in that namespace
    4. Unlock ManageIQ domain now
    5. Select Instance/Method from any class in ManageIQ
    6. From configuration toolbar, select `Copy this method/Instance`
    Additional info: https://bugzilla.redhat.com/show_bug.cgi?id=1500956

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
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
        casecomponent: cloud
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_enhanced_playbook_debug():
    """
    Enable Embedded Ansible and add repo with playbooks. Try to create new
    service dialog and try to order the service. In the dialog, there
    should be option to enable debugging of the playbook (I believe the
    playbook is executed with -vvv option).

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tagvis_cluster_and_vm_combination():
    """
    Combine Host&Cluster with VM&Templates
    Check restricted user can see Cluster and only VMs and Templates from
    this cluster

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_creds_details():
    """
    Clicking on a cred name should show details of the Credentials.
    (Automation-Ansible-Credentials Table view showing provider creds
    added)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vm_tempate_ownership_nogroup():
    """
    test assigning no groups ownership for vm and templates
    https://bugzilla.redhat.com/show_bug.cgi?id=1330022
    https://bugzilla.redhat.com/show_bug.cgi?id=1456681
    UPDATE: There was no movement on BZ 1456681 for a long time. If this
    BZ is not resolved, we don"t know how exactly the ownership should
    behave in certain situations and this testcase will always fail.
    Assigning no group ownership should work fine.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
def test_should_be_able_to_access_services_requests_as_user():
    """
    Unexpected Error when accessing SERVICE -> REQUESTS (undefined method
    find_tags_by_grouping)
    https://bugzilla.redhat.com/show_bug.cgi?id=1576129

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Should be able to access services - requests as user
    """
    pass


@pytest.mark.manual
def test_drop_down_list_dialog_does_should_keep_default_value_for_integer_type_in_dialogs():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1554780

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        startsin: 5.9
        title: Drop Down List Dialog does should keep default value for Integer type in dialogs
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
@pytest.mark.tier(3)
def test_dynamic_drop_down_dialog_should_work_with_automate_expression_method():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1583694

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/6h
        title: Dynamic Drop Down Dialog should work with Automate Expression Method
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_server_unconfigured():
    """
    check collect all logs under server when both levels are unconfigured.
    Expected result - all buttons are disabled

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
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
        casecomponent: services
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tag_expression_and_with_or():
    """
    Combine tags with AND and OR conditions
    Check item visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automated_locale_switching():
    """
    Having the automatic locale selection selected, the appliance"s locale
    changes accordingly with user"s preferred locale in the browser.

    Polarion:
        assignee: None
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_user_cloud_cpu_quota_by_lifecycle():
    """
    test user cpu quota for cloud instance provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_stack_template_azure():
    """
    There was a new field added to Orchestration stacks to show which
    image was used to create it.  You need to verify the end points of
    this image are displayed correctly.
    This just needs to be checked every once in a while.  Perhaps once per
    build.  Should be able to automate it by comparing the yaml entries to
    the value.

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/8h
        setup: Create a stack based on a cloud image.  Go to stack details and check
               the
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_the_authentication_mode_is_displayed_correctly_for_new_trusted_forest_table_en():
    """
    verify the authentication mode is displayed correctly for new trusted
    forest table entry.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/6h
        title: verify the authentication mode is displayed correctly for
               new trusted forest table entry.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_custom_button_disable():
    """
    Check if the button is disable or not (i.e. visible but blurry)
    Steps
    1)Add Button Group
    2)Add a button to the newly created button group
    3)Add an expression for disabling button (can use simple {"tag":
    {"department":"Support"}} expression)
    4)Add the Button group to a page
    5)Check that button is enabled; if enabled pass else fail.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_cloud_host_aggregates():
    """
    Setup: Create group with tag, use this group for user creation
    1. Add tag(used in group) for cloud host aggregate via detail page
    2. Remove tag for cloud host aggregate via detail page
    3. Add tag for cloud host aggregate via list
    4. Check cloud host aggregate is visible for restricted user
    5. Remove tag for cloud host aggregate via list
    6 . Check cloud host aggregate isn"t visible for restricted user

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_zone_multiple_servers_zone_setup():
    """
    using any type of depot check collect current log function under zone.
    Zone should have multiplie servers under it. Zone should be setup,
    servers should not

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(2)
def test_tenant_visibility_service_template_items_all_parents():
    """
    Child tenants can see all service template items defined in parent
    tenants.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_host_info_scvmm():
    """
    The purpose of this test is to verify that SCVMM-SP1 hosts are not
    only added, but that the host information details are correct.  Take
    the time to spot check at least one host.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.4
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
@test_requirements.auth
@pytest.mark.tier(1)
def test_configure_ldap_authentication():
    """
    Verifies the ldap authentication mode configuration/setup on CFME
    appliance.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        testSteps:
            1. specify the authentication mode to LDAP.
            2. specify the valid credentials
            3. specify the port number, hostname and other details to
               configure the ldap authentication for CFME appliance.
        expectedResults:
            1. No Error is expected to occur by specifying the LDAP authentication mode.
            2. validation is expected to be successful with valid credentials
            3. the ldap authentication mode is expected to be successful
               after specifying the valid details.
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_quota_for_ansible_service():
    """
    test quota for ansible service

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/4h
        setup: Quota check causes errors for service provisioning when using Ansible
               Tower service types
               https://bugzilla.redhat.com/show_bug.cgi?id=1363901
        startsin: 5.5
        title: test quota for ansible service
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
        casecomponent: web_ui
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
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Check all availability zones for amazon provider
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_sui_timeline_should_display_snapshots_at_the_time_of_creation():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1490510

    Polarion:
        assignee: apagac
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: SUI : Timeline should display snapshots at the time of creation
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
@pytest.mark.tier(3)
def test_automate_git_import_deleted_tag():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1394194

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_check_my_company_all_evm_groups_filter_from_reports_schedule():
    """
    Steps to Reproduce:
    1.Navigate to Cloud Intel → Reports.
    2.Click the Schedules accordion
    3.Add a New Schedule
    4.Under Report Selection →
    Try to select custom report In Filter drop downs that you want to
    schedule
    https://bugzilla.redhat.com/show_bug.cgi?id=1559323

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/16h
        startsin: 5.9
        title: Check My Company(All EVM Groups) filter from reports schedule
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
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.power
@pytest.mark.tier(2)
def test_suspend_scvmm2016_from_collection():
    """
    Test the a VM can be Suspended, or Saved, from the Collection Page

    Polarion:
        assignee: ghubale
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_service_quota_runs_only_once():
    """
    Steps described here:
    https://bugzilla.redhat.com/show_bug.cgi?id=1317698

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
@pytest.mark.tier(1)
def test_config_manager_change_zone():
    """
    Add Ansible Tower in multi appliance, add it to appliance with UI. Try
    to change to zone where worker is enabled.
    https://bugzilla.redhat.com/show_bug.cgi?id=1353015

    Polarion:
        assignee: nachandr
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_linked_vms_opsui_sui():
    """
    Associated with BZhttps://bugzilla.redhat.com/show_bug.cgi?id=1510797
    Please follow the steps below to recreate the scenario: 1. Enable
    Embedded Ansible role.
    2. Wait until it will be enabled.
    3. Navigate to Automate/Ansible.
    4. Add ansible repository https://github.com/mkanoor/playbook.
    5. Navigate to Services->Catalogs.
    6. Expand "Catalog Items" accordion.
    7. Create "Ansible Playbook" Catalog Item.
    8. Pick "add_single_vm_to_service.yml" playbook.
    9. Navigate to Control->Explorer.
    10. Expand Actions accordion.
    11. Click Configuration->Add a new Action.
    12. In action type choose "Run Ansible Playbook".
    13. In Playbook Catalog Item choose just created catalog item.
    14. In inventory choose "Target machine" or provide a specific host.
    15. Assign this action to some event in a host or vm control policy.
    16. Assign policy profile which contains that policy to some host or
    vm.
    17. Trigger the event which assigned to the policy.
    18. Wait until the service will be provisioned.
    19. Navigate tot Services/My Services.
    20. Open details of the provisioned service, open "Provisioning" tab.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_request_filter_on_request_page():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1498237

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/4h
        title: Test Request filter on Request page
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_sui_test_snapshot_count():
    """
    create few snapshots and check if the count displayed on service
    details page is same as the number of snapshots created
    and last snapshot created is displayed on service detail page .
    Also click on the snapshot link should navigate to snapshot page .

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
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
        casecomponent: prov
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
        initialEstimate: 1/15h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_ssui_catalog_items():
    """
    Steps:
    1.Create groups with tag
    2. Create user and assign it to group
    3. As admin create service catalog and catalog item
    4. Log in as user to ssui
    5. Check catalog item list -> User should not see any items
    6. As admin set tag to catalog item
    7. As user, check visibility -> User should see tagged catalog item

    Polarion:
        assignee: anikifor
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
def test_embedded_ansible_update_bad_version_59017():
    """
    Tests updating an appliance which has embedded ansible role enabled,
    also confirms that the
    role continues to function correctly after the update has completed
    Test Source

    Polarion:
        assignee: None
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenantadmin_group_crud():
    """
    As a Tenant Admin I want to be able to create groups related to the
    roles in my tenant and assign roles
    1) Login as tenant admin
    2) Navigate to Configure - Configuration - Access Control - Groups
    3) Configuration - Add a new group
    4) Assign Group name, role and Project/tenant and click Add

    Polarion:
        assignee: mnadeem
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_sui_should_show_custom_button_dialog():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1574774

    Polarion:
        assignee: ndhandre
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI should show custom button dialog
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_ldap_invalid_user_login():
    """
    Verifies scenario"s associated with the invalid user login(negative
    test case).

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        testSteps:
            1. login with the invalid user.
            2. configure the ldap with userA in groupA, configure CFME
               for userA and groupA. Login with userA
            3. delete the userA in the ldap. try Login with userA to CFME appliance
        expectedResults:
            1. login should fail for invalid credentials.
            2. login should be successful
            3. login should fail
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
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_create_snapshot_when_no_provider_is_connected():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1440966

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : Create snapshot when no provider is connected
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_storage_managers():
    """
    Setup: Create group with tag, use this group for user creation
    1. Add tag(used in group) for storage manager via detail page
    2. Remove tag for storage manager via detail page
    3. Add tag for storage manager via list
    4. Check storage manager is visible for restricted user
    5. Remove tag for storage manager via list
    6 . Check storage manager isn"t visible for restricted user

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
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
@test_requirements.auth
@pytest.mark.tier(3)
def test_remove_display_name_for_user_in_ldap_and_verify_auth():
    """
    1. Remove display name for user in ldap and verify auth.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
        title: Remove display name for user in ldap and verify auth.
    """
    pass


@pytest.mark.manual
def test_ec2_security_group_record_values():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1540283

    Polarion:
        assignee: mmojzis
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_template_rhos7_ga_fedora_22_ext4():
    """
    test_ssa_template[rhos7-ga-fedora-22-ext4]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
        testtype: integration
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
@pytest.mark.tier(1)
def test_rhi_rules():
    """
    Verify all sub-tabs in rules and whether filter is working properly

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_change_the_search_base_for_user_and_groups_lookup_at_domain_component_():
    """
    Change the search base for user and groups lookup at domain component
    . e.g. change the search level from
    "ou=Groups,ou=prod,dc=qetest,dc=com "
    To "dc=qetest,dc=com"
    Change the ‘ldap_group_search_base’ and ‘ldap_user_search_base’ in
    /etc/sssd/sssd.conf for specific domain.
    Make sure domain_suffix is updated correctly for your ldap domain
    under test.
    Restart sssd service (service sssd restart)
    Verify configuration with dbus commands (refer MOJO)
    Verify user/group retrieval in CFME webui.
    user/group created at any hierarchy level under the tree
    dc=qetest,dc=com is expected to be retrieved.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: Change the search base for user and groups lookup at domain component .
    """
    pass


@pytest.mark.manual
def test_automation_executed_on_field_refresh_are_called_twice_in_self_service_dialogs():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1576873

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: automation executed on field refresh are called twice in self service dialogs
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_smartstate_analysis():
    """
    SmartState Analysis (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
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
@test_requirements.quota
@pytest.mark.tier(1)
def test_user_cloud_storage_quota_by_lifecycle():
    """
    test user storage quota for cloud instance provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_multiple_stack_deployment():
    """
    Create bundle of stack and provision

    Polarion:
        assignee: None
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Multiple Stack deployment
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_infra_memory_quota_by_services():
    """
    test group memory for infra vm provision by ordering services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
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
        assignee: None
        casecomponent: cloud
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_field_zone_name_whitespace():
    """
    When creating a new zone, the name can have whitespace, including
    leading and trailing characters. After saving, any leading or trailing
    whitespace is not displayed in the web UI.

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_crud():
    """
    Test the SUI snapshot timeline.
    See if the data in the timeline are corresponding to the snapshot
    actions. Try to create snapshots, revert to snapshot and delete
    snapshot and see if the timeline reflects this correctly

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/2h
        testSteps:
            1. create a new vm
            2. create two snapshots for the VM
            3. revert to the first snapshot
            4. delete all snapshots
            5. go to the VM details page, then Monitoring -> Timelines
            6. select "Management Events" and "Snapshot Activity" and click Apply
        expectedResults:
            1. vm created
            2. snapshots created
            3. revert successful
            4. delete successful
            5. timelines page displayed
            6. snapshot timeline appears, all actions are in the timeline
               and visible, the time/date appears correct
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_create_duplicate():
    """
    Create Zone with name that is already in use.

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_server_zone_setup():
    """
    using any type of depot check collect all log function under applince
    (settings under server should not be configured, under zone should be
    configured)

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.genealogy
@pytest.mark.tier(2)
def test_edit_vm():
    """
    Edit infra vm and cloud instance
    https://bugzilla.redhat.com/show_bug.cgi?id=1399141
    https://bugzilla.redhat.com/show_bug.cgi?id=1399144
    When editing cloud instance, genealogy should be present on the edit
    page.
    When you have two providers - one infra and one cloud - added, there
    should be no cloud vms displayed when setting genealogy for infra vm
    and vice-versa.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
def test_project_cloud_cpu_quota_by_enforce():
    """
    test cpu quota for project for cloud instance by enforcement

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_cloud_cpu_quota_by_lifecycle():
    """
    test group cpu quota for cloud instance provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
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
@test_requirements.service
@pytest.mark.tier(3)
def test_remove_catalog_items_from_catalog_bundle_resource_list():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1639557

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: None
        title: remove catalog items from Catalog Bundle resource list
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_state_method():
    """
    PR link (merged 2016-03-24)
    You can pass methods as states compared to the old method of passing
    instances which had to be located in different classes. You use the
    METHOD:: prefix

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
        setup: A fresh appliance.
        startsin: 5.6
        testSteps:
            1. Create an automate class that has one state.
            2. Create a method in the class, make the method output
               something recognizable in the logs
            3. Create an instance inside the class, and as a Value for the
               state use: METHOD::method_name where method_name is the name
               of the method you created
            4. Run a simulation, use Request / Call_Instance to call your
               state machine instance
        expectedResults:
            1. Class created
            2. Method created
            3. Instance created
            4. The method got called, detectable by grepping logs
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_button_can_trigger_events():
    """
    In the button creation dialog there must be MiqEvent available for
    System/Process entry.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/60h
        startsin: 5.6.1
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_host_os_info():
    """
    Checks the host's OS name and version

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_external_auth_configuration_with_ipa():
    """
    Set hostname for the appliance with FQDN
    Update /etc/hosts with IPA server ip and FQDN
    Update appliance FQDN to IPA server /etc/hosts
    Make sure, both the machine can communicate using FQDN.
    Run appliance_console and follow the steps in https://mojo.redhat.com/
    docs/DOC-1088176/edit?ID=1088176&draftID=1981816  Configuring CFME
    with external auth for IPA

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        title: External Auth configuration with IPA
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_auto_refresh_of_pages_of_sui_request_and_service_explorer_and_myorders():
    """
    https://www.pivotaltracker.com/story/show/134430901

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : Auto-refresh of pages of SUI (Request and Service Explorer and MyOrders)
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_requests_tab_exposed():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1508490
    Need to expose Automate => Requests tab from the Web UI without
    exposing any other Automate tabs (i.e. Explorer, Customization,
    Import/Export, Logs). The only way to expose this in the Web UI, is to
    enable Services => Requests, and at least one tab from the Automate
    section (i.e. Explorer, Customization, etc).

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
def test_custom_button_state_disabled():
    """
    Custom button by default will be in the enabled state. For example:
    (enabled only if VM > 0) In this case, button get enabled if condition
    true and disabled if it is false.
    Steps:
    1. Add provider
    2. Create service dialog
    3. Create custom button group in service accordion option
    5. Add button to the group. In "Advanced" tab of a button, put valid
    expression for Enablement such that condition should fail. (Make sure
    to select dialog created at step2)
    6. Create catalog from Services
    7. Create catalog item and assign dialog & catalog created in step2 &
    6 respectively.
    8. Navigate to self-service UI and Order created catalog item
    9. Click service you have ordered and check enabled custom button
    there
    Additional info:
    This enhancement feature is related to https://github.com/ManageIQ
    /manageiq-ui-service/pull/1012.

    Polarion:
        assignee: ndhandre
        casecomponent: ssui
        caseimportance: low
        caseposneg: negative
        initialEstimate: None
        startsin: 5.9
        upstream: no
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_field_zone_name_long():
    """
    When creating a new zone, the name can be up to 50 characters long,
    and displays correctly after saving.

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_verify_retrieve_ldaps_groups_works_fine_for_ldap_user_from_cfme_webui():
    """
    Configure external auth as in TC#1
    Retrieve user groups in Access Control->groups->configuration->New
    group
    Monitor the audit.log and evm.log for no errors.
    validate the data comparing with ldap server data.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        title: verify retrieve ldaps groups works fine for ldap user from CFME webui.
    """
    pass


@pytest.mark.manual
@test_requirements.service
def test_retire_ansible_service_bundle():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1363897
    Retirement state machine does not handle Ansible Tower services when
    part of a bundle

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
        title: test retire ansible service bundle
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_quota_calculation_using_service_dialog_overrides():
    """
    Bz- https://bugzilla.redhat.com/show_bug.cgi?id=1492158

    Polarion:
        assignee: ghubale
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.8
        title: Test Quota calculation using service dialog overrides.
        testSteps:
            1. create a new domain quota_test
            2.Using the Automate Explorer, copy the
              ManageIQ/System/CommonMethods/QuotaMethods/requested method
              to the quota_test domain.
            3. Import the attached dialog . create catalog and catalog
               item using this dialog
            4. create a child tenant and set quota. create new group and
               user for this tenant.
            5. login with this user and provision by overidding values
            6. Also test the same for user and group quota source type
        expectedResults:
            1.
            2. quota should be denied
            3.
            4.
            5.
            6.
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
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_generic_object_details_displayed_from_a_service_do_not_include_associations_of_that_g():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1576828

    Polarion:
        assignee: nansari
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
        title: Generic object details displayed from a service do not
               include associations of that generic object
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
@test_requirements.rep
def test_distributed_zone_in_different_networks():
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: infra
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1460263
    # appliance_console
    -> Stop EVM Server Processes
    -> Start EVM Server Processes
    # cd /var/www/miq/vmdb/
    # bin/rails c
    irb(main):001:0> MiqQueue.where(:state => "error")

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/15h
        title: Verify that errored-out queue messages are removed
    """
    pass


@pytest.mark.manual
@test_requirements.filter
def test_search_is_displayed_myservices():
    """
    1) Go to Services -> My Services
    2) Check whether Search Bar and Advanced Search button are displayed

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
def test_satellite_credential_validation_times_out_with_error_message():
    """
    Bug 1564601 - Satellite credential validation times out with no error
    message
    https://bugzilla.redhat.com/show_bug.cgi?id=1564601
    When adding a new Satellite configuration provider, if the URL cannot
    be accessed because of a firewall dropping packets, then credential
    validation should time out after 2 minutes with a flash message.

    Polarion:
        assignee: tpapaioa
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/6h
        title: Satellite credential validation times out with error message
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_azure_provisioning_service_owner():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1352903

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: Test azure provisioning service owner
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
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/6h
        title: Verify session timeout works fine for external auth.
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_tag_mapping_azure_instances():
    """
    Requirement: Have an azure provider
    1) Create an instance and tag it with test:testing
    2) Go to Configuration -> CFME Region -> Map Tags
    3) Add a tag:
    Entity: Instance (Microsoft Azure)
    Label: test
    Category: Testing
    4) Refresh provider
    5) Go to summary of that instance
    6) In Smart Management field should be:
    My Company Tags testing: Testing
    7) Delete that instance

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(2)
def test_tenant_visibility_vms_all_childs():
    """
    Members of parent tenant can see all VMs/instances created by users in
    child tenants.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_button_groups_created_on_orchestration_type_heat_service_catalog_items_are_not_seen_o():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1496190

    Polarion:
        assignee: sshveta
        casecomponent: services
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1516721

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        title: Test default value on Dropdown inside Dialog
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_check_disk_allocation_size_scvmm():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1490440
    Steps to Reproduce:
    1.Provision VM and check it"s "Total Datastore Used Space"
    2.go to VMM and create Vm"s Checkpoint
    3.open VM Details check - "Total Datastore Used Space"

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/2h
        title: Check disk allocation size [SCVMM]
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_tenant_ldap_group_switch_between_tenants():
    """
    User who is member of 2 or more LDAP groups can switch between tenants
    1) Configure LDAP authentication on CFME
    2) Create 2 different parent parent-tenants
    - marketing
    - finance
    2) Create groups marketing and finance (these are defined in LDAP) and
    group names in LDAP and CFME must match
    Assign these groups to corresponding tenants and assign them EvmRole-
    SuperAdministrator roles
    3) In LDAP we have 3 users:
    - bill -> member of marketing group
    - jim -> member of finance group
    - mike -> is member of both groups
    4) Login as mike user who is member of 2 different tenants
    5) User is able switch between groups - switching is done in a way
    that current current group which is chosen is writtent into DB as
    active group. Therefore user who is assigned to more groups must login
    to Classic UI and switch to desired group. Afterthat he is able login
    via Self Service UI to desired tenant

    Polarion:
        assignee: mnadeem
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
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
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_user_groups_can_be_retrieved_from_trusted_forest():
    """
    verify user groups can be retrieved from "trusted forest", when the
    "import roles from home forest" is unchecked.configuration:
    1. Create the user "ldaptest" and group "engineering" in ldap:"cfme-
    qe-ldap", and add "ldaptest" user to "engineering" group.
    2. Create the user "ldaptest" and group "cfme" in ldap:"cfme-qe-ipa"
    and add "ldaptest" user to "cfme" group.
    Steps :
    1. Login as "admin" and navigate to
    configure->configuration->authentication
    2. change the authentication mode to "ldap"
    3. specify the hostname for the "cfme-qe-ipa", as the primary ldap.
    4. in the "Role Settings" check "Get User Groups from LDAP", observe
    that "Trusted Forest Settings" table displayed below. specify "Base
    DN" and "Bind DN"
    5. click on "+" to add "Trusted Forest Settings", specify HostName as
    "cfme-qe-ldap",enter valid Base DN, Bind DN and "Bind Password" click
    add the trusted forest and click "Save"
    6. navigate to "access control"-> "groups"->"add new group", check
    (Look Up LDAP Groups), specify the user "ldaptest", click retrieve.
    Observe that only the groups(cfme) from Primary ldap (cfme-qe-ipa) are
    retrieved. no group(engineering) from "cfme-qe-ldap" is reqtrieved.
    7. manually add the group "engineering", logout and login as
    "ldaptest". Observe that login fails for the user "ldaptest"

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: verify user groups can be retrieved from "trusted forest"
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_catalog_item_changing_the_provider_template_after_filling_all_tabs():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1240443

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
        title: Catalog Item : Changing the provider(template) after filling all tabs
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_ha():
    """
    Tower should be highly available. p2

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_scheduler_singleton():
    """
    Scheduler (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_azure_credentials():
    """
    Add Azure credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_create_azure_vm_from_azure_image():
    """
    This step takes a while.  You need to run a long powershell script
    against the image uploaded in Test Case RHCF3-11273
    Make the VM
    Config SSH support
    Config DNS is desired.
    SSH into new VM with Azure Public IP address and verify it has booted
    correctly.
    Optionally - Use HTTP to DNS into the appliance web ui and make sure
    you can log in.

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        initialEstimate: 1/2h
        setup: # Virtual Machine Name - as it appears in Azure
               $VMName = "myVmName"
               $ResourceGroupName = "CFMEQE-Main"
               Break
               # Existing Azure Deployment Values - Video with instructions
               forthcoming.
               $AvailabilitySetName = "cfmeqe-as-free"
               $AzureLocation = "East US"
               $VMDeploymentSize= "Standard_A1"
               $StorageAccountName = "cfmeqestore"
               $BlobContainerName = "templates"
               $VHDName = "cfme-azure-56013.vhd"
               $VirtualNetworkName = "cfmeqe"
               $NetworkSecurityGroupName = "cfmeqe-nsg"
               $VirtualNetworkSubnetName = "default"
               $VirtualNetworkAddressPrefix = "10.0.0.0/16"
               $VirtualNetworkSubnetAddressPrefix = "10.0.0.0/24"
               # Create VM Components
               $StorageAccount = Get-AzureRmStorageAccount -ResourceGroupName
               $ResourceGroupName -Name $StorageAccountName
               $InterfaceName = $VMName
               $NetworkSecurityGroupID = Get-AzureRmNetworkSecurityGroup -Name
               $NetworkSecurityGroupName -ResourceGroupName $ResourceGroupName
               $PIp = New-AzureRmPublicIpAddress -Name $InterfaceName
               -ResourceGroupName $ResourceGroupName -Location $AzureLocation
               -AllocationMethod Dynamic -Force
               $SubnetConfig = New-AzureRmVirtualNetworkSubnetConfig -Name
               $VirtualNetworkSubnetName -AddressPrefix
               $VirtualNetworkSubnetAddressPrefix
               $VNet = New-AzureRmVirtualNetwork -Name $VirtualNetworkName
               -ResourceGroupName $ResourceGroupName -Location $AzureLocation
               -AddressPrefix $VirtualNetworkAddressPrefix -Subnet $SubnetConfig
               -Force
               $Interface = New-AzureRmNetworkInterface -Name $InterfaceName
               -ResourceGroupName $ResourceGroupName -Location $AzureLocation
               -SubnetId $VNet.Subnets[0].Id -PublicIpAddressId $PIp.Id -Force
               $AvailabilitySet = Get-AzureRmAvailabilitySet -ResourceGroupName
               $ResourceGroupName -Name $AvailabilitySetName
               $VirtualMachine = New-AzureRmVMConfig -VMName $VMName -VMSize
               $VMDeploymentSize -AvailabilitySetID $AvailabilitySet.Id
               $VirtualMachine = Add-AzureRmVMNetworkInterface -VM $VirtualMachine
               -Id $Interface.Id
               $OSDiskUri = $StorageAccount.PrimaryEndpoints.Blob.ToString() +
               $BlobContainerName + "/" + $VHDName
               $VirtualMachine = Set-AzureRmVMOSDisk -VM $VirtualMachine -Name
               $VMName -VhdUri $OSDiskUri -CreateOption attach -Linux
               # Create the Virtual Machine
               New-AzureRmVM -ResourceGroupName $ResourceGroupName -Location
               $AzureLocation -VM $VirtualMachine
        startsin: 5.6
        teardown: When you"re done, delete everything.  Make sure at a minimum that the
                  VM is completely Stopped in Azure.
        title: Create Azure VM from Azure image
        upstream: no
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_service_dialog_import():
    """
    Steps:
    1. Navigate to Automation > Automate > Customization
    2. In `Import/Export` accordion, try to upload sample service dialog
    How to check dialog uploaded successful?
    Recheck it from `Export` table on same page or from `Service Dialogs`
    accordion
    Note:
    CFME don"t support export from a version N to a version N-1
    Additional info:
    https://bugzilla.redhat.com/show_bug.cgi?id=1535419

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_the_trusted_forest_settings_table_display_in_authentication_page():
    """
    verify the trusted forest settings table display in authentication
    page. switch between the authentication modes and check the trusted
    forest settings table does not disappear.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/6h
        title: verify the trusted forest settings table display in authentication page.
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_date_should_be_change_in_editing_reports_scheduled():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1446052
    Steps to Reproduce:
    1. Edit schedule report
    2. Under "Timer" Select "monthly"  every "month"
    3. Try to change "Starting Date"

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.3
        title: Date should be change In editing reports scheduled
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
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_session_timeout():
    """
    Set the session timeout to 5 mins. Check if session times out.

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        initialEstimate: 1/4h
        startsin: 5.8
        title: SUI : Session Timeout
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_rest_metric_rollups():
    """
    This test checks that the we get a correct reply for our query.

    Polarion:
        assignee: pvala
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_provider_discover_error_azure():
    """
    Same as discover provider, only we want to make sure to enter an
    incorrect value for all fields and make sure it doesn"t accept the
    entry as valid. (Provider will not discover)

    Polarion:
        assignee: pvala
        casecomponent: cloud
        caseimportance: medium
        caseposneg: negative
        endsin: 5.8
        initialEstimate: 1/8h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_switch_groups_works_fine_for_user_with_multiple_groups_assigned():
    """
    Assign ldap user to multiple default groups.
    Login as user and verify switch groups works fine.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify switch groups works fine for user with multiple groups assigned.
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
        casecomponent: appl
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
        assignee: None
        casecomponent: optimize
        initialEstimate: 1/4h
        testSteps:
            1. setup c&u for provider and wait for bottleneck events
        expectedResults:
            1. summary graph is present and clickeble
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_custom_button_language():
    """
    There was bug with usecase before.
    Additional info - https://bugzilla.redhat.com/show_bug.cgi?id=1568417
    Steps:
    1. set the language to french
    2. go to automation-> automate -> customization
    Expected:
    The custom buttons tree should not empty from automation-> automate ->
    customization

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: low
        customerscenario: true
        initialEstimate: 1/8h
        startsin: 5.9
        testtype: nonfunctional
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_pod_appliance_basic_ipa_auth():
    """
    auth from ipa server should work

    Polarion:
        assignee: izapolsk
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_against_machine():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against machine with machine credentials

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_rhos7_ga_fedora_22_ext4():
    """
    test_ssa_files[rhos7-ga-fedora-22-ext4]

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu instance.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/3h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_upload_azure_image_to_azure():
    """
    Upload image copied from RHCF3-11271 to azure using powershell
    similiar the script in the setup section.

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/2h
        setup: # Video Demo Script - Upload VHD to Azure
               # You have to log in via Login-AzureRmAccount
               Get-AzureRmSubscription -SubscriptionId "9ee63d8e-aee7-4121-861c-
               d67a5b8d231e" -TenantId "2e64678d-2fa8-40ed-8922-c9b8e2c3f100" |
               Select-AzureRmSubscription
               $ResourceGroupName = "CFMEQE-Main"
               $BlobLocation = "https://cfmeqestore.blob.core.windows.net/"
               $BlobContainer = "templates"
               $BlobName = "tmpl-osDisk.vhd"
               $BlobDestination = $BlobLocation + $BlobContainer + "/" + $BlobName
               $LocalFilePath = "C:\tmp\"
               $LocalFileName = "cfme-azure-5.6.0.13-1.x86_64.vhd"
               $LocalFile = $LocalFilePath + $LocalFileName
               Add-AzureRmVhd -ResourceGroupName $ResourceGroupName -Destination
               $BlobDestination -LocalFilePath $LocalFile -NumberOfUploaderThreads 8
        startsin: 5.6
        title: Upload Azure image to Azure
        upstream: no
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_network_credentials():
    """
    Add Network credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.9
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_inventory_refresh_westindia_azure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1473619

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_misclicking_checkbox_vms():
    """
    BZ1627387

    Polarion:
        assignee: anikifor
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/8h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1627387
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_sui_while_ordering_service_catalog_the_dynamic_drop_down_dialogs_fields_should_auto_r():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1568342
    SUI - While ordering service catalog, the dynamic drop-down dialogs
    fields do not auto-refreshed

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI - While ordering service catalog, the dynamic drop-down
               dialogs fields should auto-refresh
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
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_credentials_changed():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1552274

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_set_hostname_from_appliance_console_and_configure_external_auth():
    """
    set hostname from appliance_console and configure external_auth.
    Steps:
    1. ssh to appliance, and run appliance_console command
    2. change the appliance hostname with valid FQDN
    3. Verify External auth configuration does not fail.
    https://bugzilla.redhat.com/show_bug.cgi?id=1360928

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/3h
        title: set hostname from appliance_console and configure external_auth
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_infra_cpu_quota_by_lifecycle():
    """
    test group cpu quota for infra vm provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.tag
@pytest.mark.tier(2)
def test_restricted_user_rbac_for_access_control():
    """
    Related to BZ#1311399
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
        assignee: None
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_files_unicode():
    """
    Make sure https://bugzilla.redhat.com/show_bug.cgi?id=1221149 is fixed

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(2)
def test_log_scvmm_rollover_scvmm():
    """
    Need to verify that the scvmm.log rolls over at the end of each day
    and is zipped up.

    Polarion:
        assignee: anikifor
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_ldap_group_retrieval_works_fine_for_groups_with_descriptions_which_are_base64_():
    """
    verify ldap group retrieval works fine for groups with descriptions
    which are base64 decoded , one random sample having an "é"
    Refer the BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1367600

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/4h
        title: verify ldap group retrieval works fine for groups with
               descriptions which are base64 decoded
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1518926
    When a VM is retiring or retired, the VM should show a "Retirement
    State" field, not "Retirement state".

    Polarion:
        assignee: tpapaioa
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/15h
        title: VM's Retirement State field is capitalized correctly
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_catalog_item_for_ansible_playbook():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.8
        title: Catalog Item for Ansible Playbook
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_ansible_catalog_items():
    """
    test adding new playbook catalogs and items to remote and global
    region
    https://bugzilla.redhat.com/show_bug.cgi?id=1449696

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_rhos_credentials():
    """
    Add RHOS credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.9
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
@pytest.mark.tier(2)
def test_public_ip_reuse_azure():
    """
    Testing Public Ip reuse
    prerequirements:
    Free Public IP associated with Network interface but not assigned to
    any VM
    Select PubIP on Environment tab during provisioning

    Polarion:
        assignee: None
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
        tags: provision
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_service_infra_tenant_quota_cpu_default_entry_point():
    """
    tenant service cpu quota validation for infra provider using default
    entry point

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_service_ui_should_not_time_outs_after_10_mins_even_if_you_are_interacting_with_it():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1591436

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/16h
        startsin: 5.8
        title: Service UI should not time-outs after 10 mins even if you
               are interacting with it
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
        casecomponent: infra
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
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_field_zone_description_leading_whitespace():
    """
    Leading whitespace in description

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
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
        casecomponent: candu
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_edit_catalog_bundle():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1631040

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Edit catalog bundle
    """
    pass


@pytest.mark.manual
def test_duplicate_groups_when_setting_ownership_to_multiple_items():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1589009
    1. Navigate to Infrastructure -> Provider -> Vmware
    2. select multiple vms and go to Configuration -> Set ownership
    3. Under group list, duplicate group names listed.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
        title: Test duplicate groups when setting ownership to multiple items
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_service_cloud_tenant_quota_storage_default_entry_point():
    """
    tenant service storage quota validation for cloud provider using
    default entry point

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.quota
def test_orphaned_vms_get_excluded_from_used_quota_counts():
    """
    Test that used Quota gets recounted and reduced, when a VM is
    orphaned.
    https://bugzilla.redhat.com/show_bug.cgi?id=1515979

    Polarion:
        assignee: mkourim
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
        title: Test orphaned VMs get excluded from used quota counts
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_custom_button_state_enabled():
    """
    Custom button by default will be in the enabled state, but it can be
    also used by putting positive expressions. For example: (enabled only
    if VM > 0) In this case, button get enabled if the condition is true
    and disabled if it is false.
    Steps:
    1. Add provider
    2. Create service dialog
    3. Create custom button group in service accordion option
    5. Add button to the button group. In "Advanced" tab of button, put
    valid expression for visibility (Make sure to select dialog created at
    step2)
    6. Create catalog from Services
    7. Create catalog item and assign dialog & catalog created in step2 &
    6 respectively.
    8. Navigate to self-service UI and Order catalog item
    9. Check enabled custom button by clicking service you have ordered
    Expression used while test:  COUNT OF Service.User.VMs > -1
    Additional info:
    [1]This enhancement feature is related to https://github.com/ManageIQ
    /manageiq-ui-service/pull/1012.
    [2]Screenshot attached

    Polarion:
        assignee: ndhandre
        casecomponent: ssui
        caseimportance: low
        initialEstimate: None
        startsin: 5.9
        upstream: no
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_standard_output_non_ascii_hostname():
    """
    Look for Standard ouptut
    https://bugzilla.redhat.com/show_bug.cgi?id=1534039

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_add_private_repo():
    """
    Ability to add private repo with SCM credentials.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_report_export_import_run_custom_report():
    """
    Steps:1. generate a report from an affected custom report
    2. export the custom report
    3. import the custom report
    4. generate a new report of that custom reportall rows behave
    consistently
    https://bugzilla.redhat.com/show_bug.cgi?id=1498471

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_service_name():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1505929
    After creating the service using ansible playbook type add a new text
    field to service dialog named "service_name" and then use that service
    to order the service which will have a different name than the service
    catalog item.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_authentication_user_not_in_ldap_but_in_db():
    """
    User is not able to authenticate if he has account in CFME DB but not
    in LDAP.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_service_ui_should_take_user_default_language():
    """
    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: Service UI should take 'user default' language
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_timeout():
    """
    Set timeout to 5 minutes.
    Wait 6 minutes.
    Click on anything.
    There should be redirection to login view.
    Log in.
    There should be redirection to dashboard view.

    Polarion:
        assignee: anikifor
        caseimportance: medium
        initialEstimate: 1/4h
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
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_change_appliance_zone():
    """
    Move an appliance from one zone to another.

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
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
def test_ec2_tags_images():
    """
    Requirement: Have an ec2 provider
    1) Select an AMI in AWS console and tag it with test:testing
    2) Refresh provider
    3) Go to summary of this image  and check whether there is
    test:testing in Labels field
    4) Delete that tag

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
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
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: Cloud Key pair validation
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provider_log_level():
    """
    Polarion:
        assignee: anikifor
        casecomponent: infra
        initialEstimate: 1/4h
        setup: Tests that log level in advanced settings affects log files
               Steps:
               1. Change log level to debug
               2. Refresh provider
               3. Check logs contain debug level
               4. Reset level back
        upstream: yes
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
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_repo_url_validation():
    """
    After all processes are running fill out a new repo with resolvable
    /un-resolvable url, use the validation button to check its correct.
    https://bugzilla.redhat.com/show_bug.cgi?id=1478958

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.power
@pytest.mark.tier(2)
def test_restart_guest_scvmm2016():
    """
    This test performs the Restart Guest from the LifeCycle menu which
    invokes the Hyper-V Guest Services Integration command.  This
    gracefully exits and restarts the Windows OS rather than just powering
    off and back on.
    From collections page, select the VM and click "Restart Guest"
    On SCVMM powershell, use "$vm = Get-VM -name "name_of_vm"; Find-SCJob
    -objectId $vm.id -recent" to verify VM history shows "Shut down
    virtual machine" instead of "power off"

    Polarion:
        assignee: ghubale
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_restart_guest_scvmm():
    """
    This test performs the Restart Guest from the LifeCycle menu which
    invokes the Hyper-V Guest Services Integration command.  This
    gracefully exits and restarts the Windows OS rather than just powering
    off and back on.
    From collections page, select the VM and click "Restart Guest"
    On SCVMM powershell, use "$vm = Get-VM -name "name_of_vm"; Find-SCJob
    -objectId $vm.id -recent" to verify VM history shows "Shut down
    virtual machine" instead of "power off"

    Polarion:
        assignee: ghubale
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_create_schedule_for_base_report_hourly():
    """
    Create schedule that runs report hourly during the day. Check it was
    ran successfully

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automate_git_import_case_insensitive():
    """
    bin/rake evm:automate:import PREVIEW=false
    GIT_URL=https://github.com/mkanoor/SimpleDomain REF=test2branch
    This should not cause an error (the actual name of the branch is
    Test2Branch).

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_custom_button_enable():
    """
    Check if the button is enabled or not
    Steps
    1)Add Button Group
    2)Add a button to the newly created button group
    3)Add an expression for enabling button
    4)Add the Button group to a page
    5)Check that button is enabled; if enabled pass else fail.

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_retire_non_ascii():
    """
    Retire ansible playbook service with non_ascii host

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_database_user_login_fails_with_external_auth_configured():
    """
    Login with user registered to cfme internal database.
    Authentication expected to fail, check audit.log and evm.log for
    correct log messages.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify DataBase user login fails with External auth configured.
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
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        title: Verify invalid user login fails
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_assert_failed_substitution():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1335669

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_subscription_multiple_azure():
    """
    Azure cloud providers are added to an appliance, not only by region
    like other cloud providers, but by subscription as well.  This allows
    customer to further refine access permissions.
    For CFME-QE, we have two official subscriptions.  Dajo"s MSDN account
    9ee63d8e-aee7-4121-861c-d67a5b8d231e and our PayGo account c9e72ccc-
    b20e-48bd-a0c8-879c6dbcbfbb
    Need to add one provider for the same account and region for each of
    the above subscriptions.  The rest of the data is in the yamls  The
    test passes when each "provider" contains only the relevant data.  You
    can verify this inside of Azure.

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
        setup: Create an appliance
        startsin: 5.7
        upstream: yes
        testSteps:
            1. Add a provider with subscription 1
            2. Add a provider with subscription 2
        expectedResults:
            1. Correct subscription VMs and data appear
            2. Correct subscription VMs and data appear.
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(3)
def test_service_ansible_playbook_order_non_ascii():
    """
    test ordering ansible playbook service with non ascii characters in
    the host

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_entries_shouldnt_be_mislabeled_for_dropdown_element_in_dialog_editor():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1597802

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/16h
        startsin: 5.10
        title: Entries Shouldn't be Mislabeled for Dropdown element in Dialog Editor
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_my_settings_default_views_alignment():
    """
    Go to My Settings -> Default Views
    See that all icons are aligned correctly

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/20h
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
        casecomponent: appl
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
        casecomponent: prov
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
        assignee: mkourim
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
def test_configure_icons_roles_by_server():
    """
    Go to Settings -> Configuration and enable all Server Roles.
    Navigate to Settings -> Configuration -> Diagnostics -> CFME Region ->
    Roles by Servers.
    Click through all Roles and look for missing icons.

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/15h
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
        casecomponent: report
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
@test_requirements.ssui
@pytest.mark.tier(3)
def test_opening_ssui_and_regular_ui_tab_in_same_browser_and_then_edit_catalog():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1321655

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
        title: Opening SSUI and regular UI tab in same browser and then edit catalog
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_refresh_azure_provider_with_empty_ipv6_config_on_vm():
    """
    test case to cover -
    https://bugzilla.redhat.com/show_bug.cgi?id=1468700
    1) prepare azure  with https://mojo.redhat.com/docs/DOC-1145084
    2) refresh provider - check logs

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_active_tasks_get_timed_out_when_they_run_too_long():
    """
    active tasks get timed out when they run too long
    Bug 1397600 - After killing reporting worker, report status still says
    Running
    https://bugzilla.redhat.com/show_bug.cgi?id=1397600
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.7
        title: active tasks get timed out when they run too long
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
def test_reconfigure_existing_duplicate_orders():
    """
    decs

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_zone():
    """
    using any type of depot check collect current log function under zone
    (using structure one server under zone, zone and server should be
    configured)

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.power
@pytest.mark.tier(2)
def test_power_controls_on_archived_vm():
    """
    1)add any Cloud provider
    2)provision VM
    3)delete it (we need Archived VM)
    4)open Archived Vms/or All Vms and find your VM
    5)select it"s Quadicon and/or open it"s Details
    6)power menu should be Disabled

    Polarion:
        assignee: ghubale
        casecomponent: cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/10h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_report_secondary_display_filter_should_be_editable():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1565171
    Steps to Reproduce:
    1.Create report based on container images
    2. Select some fields for the report
    3. ON the filter tab add primary filter
    4. Add secondary filter
    5. try to edit the secondary filter.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        title: Report secondary (display) filter should be editable
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_playbooks_tag():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1526218
    RBAC - tag playbooks and allow user to see just this taged playbook.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
def test_ordering_service_by_non_admin_user():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1546944
    1. Go to Access Control, Create a role named "service_role" with below
    roles should be enabled i.e. Compute and Services.
    2. Create a user i.e. "service_user" based on this "service_role"
    3. Login with service_user and while ordering the catalog, it is
    throwing 403 Forbidden exception.

    Polarion:
        assignee: apagac
        casecomponent: infra
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_provider_inventory_singleton():
    """
    Provider Inventory (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_cold_vsphere67_nested_independent_persistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_cold_vsphere67_nested_persistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_cold_vsphere67_nested_independent_persistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_cold_vsphere67_nested_independent_nonpersistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_cold_vsphere67_nested_independent_nonpersistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
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
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_provider_operations():
    """
    Provider Operations (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
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
@pytest.mark.tier(2)
def test_vm_volume_specchar1_scvmm():
    """
    Special Test to verify that VMs that have Volumes with no drive letter
    assigned don"t cause systemic SCVMM provider errors.  This is a low
    priority test.
    https://bugzilla.redhat.com/show_bug.cgi?id=1353285

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/4h
        startsin: 5.6.1
        upstream: no
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
        casecomponent: ssui
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
@test_requirements.ssui
@pytest.mark.tier(2)
def test_notifications_should_appear_in_sui_after_enableing_embedded_ansible_role():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1637512

    Polarion:
        assignee: nansari
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/16h
        title: Notifications should appear in SUI after Enableing Embedded Ansible Role
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_able_to_access_openstack_instance_console_from_self_service_portal():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1624573

    Polarion:
        assignee: nansari
        casecomponent: ssui
        initialEstimate: 1/2h
        startsin: 5.9
        title: Able to access Openstack instance console from self service portal
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
@pytest.mark.tier(2)
def test_vm_terminate_deletedisk_azure():
    """
    New for 5.6.1, when terminating a VM in Azure, we need to go to the
    storage account and make sure the disk has also been removed.  You can
    check the VM details for the exact disk location prior to deleting.
    Note that Azure itself does not delete the disk when a VM is deleted,
    so this may initially cause some confusion.
    https://bugzilla.redhat.com/show_bug.cgi?id=1353306

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.6.1
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_import_namespace_attributes_updated():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1440226 1. Export an
    Automate model
    2. Change the display name and description in the exported namespace
    yaml file
    3. Run an import with the updated data
    4. Check if the namespace attributes get updated.Display name and
    description attributes should get updated

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_configuration_management_configured_system():
    """
    Tag a configuration management's configured system and check for its
    visibility

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_edit_chargeback_for_projects_report():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1485006

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_service_infra_tenant_quota_memory_default_entry_point():
    """
    tenant service memory quota validation for infra provider using
    default entry point

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.power
@pytest.mark.tier(2)
def test_power_contols_on_vm_in_stack_cloud():
    """
    1.Provision a VM via Service (Orchestration template - azure/ec2/rhos)
    2.Navigate to cloud->stacks->select a stack
    3.click on the instance in relationship section of stack summary page
    4.check power controls

    Polarion:
        assignee: ghubale
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.6
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
        assignee: None
        casecomponent: config
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
        casecomponent: infra
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: infra
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1514594
    Check to see if the Add provider screen has the Host VNC Start Port
    and Host VNC End port.

    Polarion:
        assignee: apagac
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: infra
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
def test_html5_console_firefox_rhevm41_fedora28_vnc():
    """
    HTML5 test

    Polarion:
        assignee: apagac
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1597393VMware VNC Remote
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1573739

    Polarion:
        assignee: apagac
        casecomponent: infra
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: infra
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
        casecomponent: appl
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
        casecomponent: appl
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1525692

    Polarion:
        assignee: apagac
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
        casecomponent: appl
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
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_zone_multiple_servers():
    """
    using any type of depot check collect current log function under zone,
    zone has multiplie servers under it. Zone and all servers should have
    theire own settings

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
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
@test_requirements.config_management
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
        casecomponent: cloud
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(2)
def test_monitor_ansible_playbook_std_output():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1444853

    Polarion:
        assignee: apagac
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/4h
        title: Monitor Ansible playbook std output
    """
    pass


@pytest.mark.manual
@test_requirements.discovery
def test_add_cloud_provider_screen():
    """
    Add cloud provider using Add Provider screen:
    Open Stack:
    -test Name
    -test incorrect format of Name
    (all combinations of following)
    -test Hostname
    -test incorrect format of Hostname
    -test incorrect Hostname
    -test Security Protocol
    -test incorrect Security Protocol
    -test Username
    -test incorrect format of Username
    -test incorrect Username
    -test Password
    -test incorrect format of Password
    -test incorrect Password
    -test Validate
    -test switching Security Protocol
    Events > AMQP
    (all combinations of following)
    -test Hostname
    -test incorrect format of Hostname
    -test incorrect Hostname
    -test API Port
    -test incorrect format of API Port
    -test incorrect API Port
    -test Security Protocol
    -test incorrect Security Protocol
    -test Username
    -test incorrect format of Username
    -test incorrect Username
    -test Password
    -test incorrect format of Password
    -test incorrect Password
    -test Validate
    -test switching Security Protocol
    Amazon EC2:
    -test Name
    -test incorrect format of Name
    (all combinations of following)
    -test Region
    -test incorrect Region
    -test Access Key ID
    -test incorrect format of Access Key ID
    -test incorrect Access Key ID
    -test Secret Access Key
    -test incorrect format of Secret Access Key
    -test incorrect Secret Access Key
    -test Confirm Secret Access Key
    -test incorrect format of Confirm Secret Access Key
    -test incorrect Confirm Secret Access Key
    -test Validate
    Azure:
    -test Name
    -test incorrect format of Name
    (all combinations of following)
    -test Region
    -test incorrect Region
    -test Tenant ID
    -test incorrect format of Tenant ID
    -test incorrect Tenant ID
    -test Subscription ID
    -test incorrect format of Subscription ID
    -test incorrect Subscription ID
    (all combinations of following)
    -test Client ID
    -test incorrect format of Client ID
    -test incorrect Client ID
    -test Client Key
    -test incorrect format of Client Key
    -test incorrect Client Key
    -test Confirm Client Key
    -test incorrect format of Confirm Client Key
    -test incorrect Confirm Client Key
    -test Validate
    Google Compute Engine
    -test Name
    -test incorrect format of Name
    (all combinations of following)
    -test Region
    -test incorrect Region
    -test Project
    -test incorrect format of Project
    -test incorrect Project
    -test Service Account JSON
    -test incorrect format of Service Account JSON
    -test incorrect Service Account JSON
    -test Validate

    Polarion:
        assignee: pvala
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 3h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_user_has_groups():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1411424
    This method should work:  groups = $evm.vmdb(:user).first.miq_groups
    $evm.log(:info, "Displaying the user"s groups: #{groups.inspect}")

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_automate_methods_from_dynamic_dialog_should_run_as_per_designed():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1571000

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/16h
        startsin: 5.9
        title: Automate Methods from Dynamic Dialog should Run as per Designed
    """
    pass


@pytest.mark.manual
def test_custom_button_enabled_ssui_false():
    """
    Steps to Reproduce:
    1. Create a button, eg. for Service in this case. Set the visibility
    and enablement expression to eg. some tags.
    2. Create a service
    3. Go to the Self Service UI, select the service and look for the
    button and its status
    4. Repeat 3 with setting and unsetting the appropriate tags and also
    removing either or both of the expressions
    If button disable then PASS
    Additional info:
    https://bugzilla.redhat.com/show_bug.cgi?id=1509959

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_custom_button_enabled_ssui_true():
    """
    Steps to Reproduce:
    1. Create a button, eg. for Service in this case. Set the visibility
    and enablement expression to eg. some tags.
    2. Create a service
    3. Go to the Self Service UI, select the service and look for the
    button and its status
    4. Repeat 3 with setting and unsetting the appropriate tags and also
    removing either or both of the expressions
    If button enabled then PASS
    Additional info:
    https://bugzilla.redhat.com/show_bug.cgi?id=1509959

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        initialEstimate: 1/8h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_storage_profile_provision():
    """
    The VM provisioning page includes drop-down listing storage_profiles
    applicable to the ems.
    if selected vm template has storage_profile attached, that
    storage_profile is pre-selected
    datastore listing is filtered by both existing filter and the selected
    storage_profile

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_host_credentials_remote():
    """
    Validate that the host can be configured to allow remote connections,
    usually WMI.  Used for Collect Running Processes

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/4h
        upstream: yes
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
@test_requirements.report
@pytest.mark.tier(1)
def test_import_export_report():
    """
    Import and export report

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        setup: Create or Identify appliance
               (no prerequisite or provider needed for this test)
        title: Import/Export report
        testSteps:
            1. Sign up to appliance
            2. Navigate to Cloud Intelligence > Reports
            3. Select any report and create its copy
            4. Locate newly created report in My Company > Custom
            5. Navigate to Import / Export
            6. Select Custom reports
            7. Select newly copied report and select Export
            8. Download the yaml file
            9. Locate exported report in My Company > Custom
            10. Delete exported report
            11. Navigate back to Import / Export
            12. Select Choose file
            13. Locate and select previously downloaded yaml file
            14. Select Upload
            15. Locate import report in My Company > Custom
            16. Sign out
        expectedResults:
            1.
            2.
            3.
            4. Verify that canned report was copied under new name
            5.
            6. Verify you"ve been redirected to Import / Export screen
            7. Verify that yaml file download was initiated
            8.
            9.
            10.
            11.
            12. Verify File upload screen was open
            13.
            14. Verify Imported report is now again available for Export
            15. Verify report is present
            16.
    """
    pass


@pytest.mark.manual
def test_custom_button_on_catalog_item():
    """
    Steps:
    1. Add catalog_item
    2. Goto catalog detail page and select `add button` from toolbar
    3. Fill info and save button

    Polarion:
        assignee: ndhandre
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(3)
def test_service_template_provisioning_quota_for_number_of_vms_using_custom_dialog():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1455844

    Polarion:
        assignee: ghubale
        casecomponent: prov
        initialEstimate: 1/4h
        startsin: 5.8
        title: test service template provisioning quota for number of vm's using custom dialog
        testSteps:
            1. Create a service catalog with vm_name, instance_type &
               number_of_vms as fields. Set quotas threshold values for
               number_of_vms to 5 and provision service catalog with vm
               count as 10.
        expectedResults:
            1. should get quota exceeded message
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_verify_external_authentication_with_openldap_proxy_to_3_different_domains():
    """
    verify external authentication with OpenLDAP proxy to 3 different
    domains
    refer the bz: https://bugzilla.redhat.com/show_bug.cgi?id=1306436

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: verify external authentication with OpenLDAP proxy to 3 different domains
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_distributed_zone_failover_notifier_singleton():
    """
    Notifier (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
def test_custom_button_visible_ssui_false():
    """
    Steps to Reproduce:
    1. Create a button, eg. for Service in this case. Set the visibility
    and enablement expression to eg. some tags.
    2. Create a service
    3. Go to the Self Service UI, select the service and look for the
    button and its status
    4. Repeat 3 with setting and unsetting the appropriate tags and also
    removing either or both of the expressions
    If button hidden then PASS
    Additional info:
    https://bugzilla.redhat.com/show_bug.cgi?id=1509959

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseposneg: negative
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_custom_button_visible_ssui_true():
    """
    Steps to Reproduce:
    1. Create a button, eg. for Service in this case. Set the visibility
    and enablement expression to eg. some tags.
    2. Create a service
    3. Go to the Self Service UI, select the service and look for the
    button and its status
    4. Repeat 3 with setting and unsetting the appropriate tags and also
    removing either or both of the expressions
    If button visible then PASS
    Additional info:
    https://bugzilla.redhat.com/show_bug.cgi?id=1509959

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
def test_superadmin_tenant_admin_crud():
    """
    Super admin is able to create new tenant administrator
    1) Create new role by copying EvmRole-tenant_administrator
    2) Create new group and choose role created in previous step and your
    tenant
    3) Create new tenant admin user and assign him into group created in
    previous step
    4) Update the user details and delete the user.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_self_service_ui_should_honor_some_service_dialog_settings():
    """
    SSUI should honor dialog settings.

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        initialEstimate: 1/4h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1518017
               Steps to Reproduce:
               1. Create service dialog with at least one dynamic drop down, click
               the "Show Refresh Button" option
               2. De-select "Load Values on Init" to disable this option for the
               dynamic drop
               3. Crete a catalog item that uses this service dialog
               4. Navigate using the normal UI to and order the catalog item.  Notice
               the dynamic drop down does not run and load values, which is as
               expected.
               5. Now, open the Self Service ui and order this same catalog item.
               Notice that the dynamic drop down will run and load values, ignoring
               the "load values on init" option.
        title: Self Service UI should honor some service dialog settings
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_service_explorer_will_also_show_child_services():
    """
    Login in SSUI
    Service explorer should show child services if any.

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: SUI : Service Explorer will also show child services
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_dialog_items_default_values_on_different_screens():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1540273

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        title: Test dialog items default values on different screens
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_verify_user_authentication_works_fine_if_default_evm_groups_are_already_created_and_a():
    """
    Create cfme default groups in ldaps domain server.
    Assign user to the default groups. e.g.  EvmGroup-administrator
    Configure cfme for ldaps external auth as in TC#1
    Authentication for ldap user is expected to be successful as cfme
    default groups are already assigned for user in ldap server.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        title: verify user authentication works fine if default evm groups
               are already created and assigned for user in ldaps
    """
    pass


@pytest.mark.manual
def test_crud_pod_appliance():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance

    Polarion:
        assignee: izapolsk
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(2)
def test_tenant_visibility_miq_ae_namespaces_all_parents():
    """
    Child tenants can see MIQ AE namespaces of parent tenants.

    Polarion:
        assignee: mnadeem
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
def test_osp_test_multi_host_migration_execution_if_more_than_one_host_present_migration_of_mu():
    """
    OSP: Test Multi-host migration execution, if more than one host
    present, migration of multiple VMs should be spread across all
    available host

    Polarion:
        assignee: ytale
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        title: OSP: Test Multi-host migration execution, if more than one
               host present, migration of multiple VMs should be spread
               across all available hosts
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(3)
def test_quota_enforcement_for_cloud_volumes():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1455349
    test quota enforcement for cloud volumes

    Polarion:
        assignee: ghubale
        casecomponent: prov
        initialEstimate: 1/4h
        startsin: 5.8
        title: test quota enforcement for cloud volumes
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_api_on_url():
    """
    The API should be present on https://<ip>/ansibleapi.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
def test_creating_second_snapshot_on_suspended_vm():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1419872

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
        title: test creating second snapshot on suspended vm
        testSteps:
            1.Navigate to  compute->infrastructure->virtual machines
              2.Select a vm with suspended state 3.Take a first snapshot.
              snapshot successful 4.Take a second snapshot
        expectedResults:
            1. Flash message Snapshot not taken since the state of the
               virtual machine has not changed since the last snapshot
               operation should be displayed in UI
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
@pytest.mark.tier(2)
def test_generic_objects_class_crud():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1650137
    1.Create Generic Objects Class
    2.Add button group
    3.Go to Generic Objects Class details page
    4.Delete the Generic Objects Class

    Polarion:
        assignee: nansari
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/16h
        title: Generic Objects Class Crud
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_service_cloud_tenant_quota_cpu_default_entry_point():
    """
    tenant service cpu quota validation for cloud provider using default
    entry point

    Polarion:
        assignee: ghubale
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_service_dialog_saving_elements_when_switching_elements():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1454428

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Test service dialog saving elements when switching elements
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_quota_units():
    """
    Steps described here:
    https://bugzilla.redhat.com/show_bug.cgi?id=1334318

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_saml_configuration_works_fine_for_cfme():
    """
    Look for the steps/instructions at http://file.rdu.redhat.com/abellott
    /manageiq_docs/master/auth/saml.html
    Verify appliance_console is updated with “External Auth: “ correctly

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/2h
        title: Verify SAML configuration works fine for CFME
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_grid_tile_list_view_pages_on_instance():
    """
    Add a cloud provider..Click on the provider , go to Instances, Click
    on Grid/ Tile or list view

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: Grid/Tile/List View pages on Instance
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_group_filter_network_provider():
    """
    Setup:
    Add cloud provider
    1. Create group and select cloud network provider in "Cluster&Hosts"
    filter
    2. Create user assigned to group from step 1
    3. As restricted user, login and navigate to Network Provider
    Result: User should see network provider + all its children
    Note: Repeat this case with tag filter

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.power
@pytest.mark.tier(2)
def test_power_operations_from_global_region():
    """
    This test case is to check power operations from Global region
    Setup is 2 or more appliances(DB should be configured manually). One
    is Global region, others are Remote
    To get this working on 5.6.4 you need to specify the :webservices =>
    :remote_miq_api user (username) and password values in the global
    region"s advanced settings for the server with the user interface
    role.
    Or Enable Central Admin for 5.7 or later

    Polarion:
        assignee: ghubale
        casecomponent: control
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.6
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_default_selection_of_dropdown_list_is_should_display_properly():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1579405

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/6h
        title: Default selection of dropdown list is should display properly
    """
    pass


@pytest.mark.manual
@test_requirements.rep
def test_distributed_diagnostics_servers_view():
    """
    The above should all be shown as different regions 1-4

    Polarion:
        assignee: tpapaioa
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_zone_zone_setup():
    """
    using any type of depot check collect current log function under zone
    (settings under server should not be configured, under zone should be
    configured)

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_user_cloud_memory_quota_by_services():
    """
    test user memory quota for cloud instance provision by ordering
    services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_disk_hot_vsphere67_nested_independent_nonpersistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
        startsin: 5.7
        title: test_vm_reconfig_add_remove_disk_hot[vsphere67-nested-
               independent_nonpersistent-thick]
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_disk_hot_vsphere67_nested_independent_persistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_disk_hot_vsphere67_nested_independent_nonpersistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_disk_hot_vsphere67_nested_independent_persistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_disk_hot_vsphere67_nested_persistent_thin():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_add_remove_disk_hot_vsphere67_nested_persistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/3h
        startsin: 5.7
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
@test_requirements.service
@pytest.mark.tier(2)
def test_custom_image_on_item_bundle_crud():
    """
    test_custom_image_on_item_bundle_crud
    Upload image and test if the uploaded icon/image shows up in the table
    .
    https://bugzilla.redhat.com/show_bug.cgi?id=1487056

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        testSteps:
            1. Create a catalog item
            2. Upload custom image
            3. remove custom image
            4. Create a catalog  bundle
            5. Upload a custom image
            6. Change custom image
        expectedResults:
            1.
            2. No error seen
            3.
            4.
            5. No error seen
            6.
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_infra_storage_quota_by_lifecycle():
    """
    test group storage quota for infra vm provision by Automate model

    Polarion:
        assignee: ghubale
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_event_catcher_process():
    """
    EventCatcher process is started after Ansible role is enabled (rails
    evm:status)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/4h
        startsin: 5.8
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
        initialEstimate: 1/10h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_copying_customization_dialog():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1342260
    1. Automate -> Customization -> Check checkbox for at least one dialog
    2. Select another dialog by clicking on it
    3. Select in Toolbar Configuration -> Copy this dialog
    4. Selected dialog should be copied and not the first checked dialog
    in alphanumerical sort

    Polarion:
        assignee: anikifor
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
def test_pod_appliance_scale():
    """
    appliance should work correctly after scale up/down

    Polarion:
        assignee: izapolsk
        initialEstimate: None
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1427484
    After clicking the bell icon in the top right of the web UI, the "x"
    in the top right corner of the notification window can be clicked to
    close it.

    Polarion:
        assignee: tpapaioa
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/15h
        startsin: 5.9
        title: Notification window can be closed by clicking 'x'
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_generate_report_custom_with_tag():
    """
    steps:
    1 Assign tag to VM, for example, departament tag,we have used
    "Discipline".
    2 Asign tag to Tenant, for example, departament tag, we have used
    "Discipline".
    3 Create report with base report "VMs and Instances" and the next
    fields: Name Departament tag.
    4 Create report with base report "Cloud Tenant" and the next fields:
    Name Departament tag.
    5 Generate the two reports.
    https://bugzilla.redhat.com/show_bug.cgi?id=1504086

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_storage_ebs_volume_crud_from_manager_list():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1449293
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
@pytest.mark.tier(2)
def test_tagvis_ansible_tower_job():
    """
    "Setup: Create group with tag, use this group for user creation
    1. Add tag(used in group) for Ansible Tower job via detail page
    2. Remove tag for Ansible Tower job via detail page
    3. Add tag for Ansible Tower job via list
    4. Check Ansible Tower job is visible for restricted user
    5. Remove tag for Ansible Tower job via list
    6 . Check ansible tower job isn"t visible for restricted user"

    Polarion:
        assignee: anikifor
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_dialog_dynamic_entry_point_should_show_full_path():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1553846

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        startsin: 5.10
        title: Dialog : dynamic entry point should show full path
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_verify_ldap_authentication_for_the_cfme_default_groups():
    """
    verify ldap authentication for the cfme default groups.
    1. define the user in ldap, and create the group in ldap with the same
    name as in cfme
    2. register the user to ldap group.
    3. verify login, monitor evm.log, aurdit.log for no errors.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        title: verify ldap authentication for the cfme default groups.
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.quota
@pytest.mark.tier(1)
def test_group_infra_cpu_quota_by_services():
    """
    test group cpu quota for infra vm provision by ordering services

    Polarion:
        assignee: ghubale
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        startsin: 5.8
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
        casecomponent: candu
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_add_repo_invalid_url():
    """
    Try to add GIT/HTPPs url which does not exist. User should be notified
    about invalid URL.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: critical
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.report
def test_schedule_add_from_report():
    """
    Add schedule from report queue

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_save_and_cancel_retirement_form_for_orchestration_stack_in_g_t_l_view():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1360417https://bugzilla.re
    dhat.com/show_bug.cgi?id=1359150

    Polarion:
        assignee: sshveta
        casecomponent: stack
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: test Save and cancel retirement form for orchestration stack in G/T/L View
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
        casecomponent: prov
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_request_check_provisioned_vm_link_on_request_page():
    """
    Provision a VM and click on the Provisioned VM Link on request page.

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.5
        title: Request : Check Provisioned VM link on Request page
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
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_custom_group_on_catalog_item():
    """
    Steps:
    1. Add catalog_item
    2. Goto catalog detail page and select `add group` from toolbar
    3. Fill info and save button

    Polarion:
        assignee: ndhandre
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
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
        assignee: jhenner
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/10h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_files_windows_utf_8_files():
    """
    Configure SSA to include c:\windows\debug\* and verify its content

    Polarion:
        assignee: sbulage
        caseimportance: medium
        initialEstimate: 1/2h
        setup: 1. Configure SSA profile to include c:\windows\debug\*
               2. Run SSA
               3. View the content of all the files (i.e., mrt.log, passwd.log,
               sammui.log, wlms.log, etc...)
        startsin: 5.3
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.provision
@pytest.mark.tier(2)
def test_add_multiple_iso_datastore():
    """
    Add two RHEV providers.
    Under Infrastructure- PXE -ISO datastore - add ISO datastore for first
    provider
    Add new datastore button should not be disabled once the datastore was
    added and second datastore can be added.

    Polarion:
        assignee: jhenner
        casecomponent: services
        initialEstimate: 1/8h
        startsin: 5.5
        title: Add multiple ISO datastore
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(2)
def test_monitor_ansible_playbook_logging_output():
    """
    bugzilla.redhat.com/1518952
    https://bugzilla.redhat.com/show_bug.cgi?id=1518952

    Polarion:
        assignee: apagac
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.8
        title: Monitor Ansible playbook Logging output
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_skip():
    """
    Test skip update of ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: config
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
               -select "Skip updates"
               -check changes have not been made
        startsin: 5.6
        testSteps:
            1. Enable Single Sign-On, SAML, Local Login then select skip updates
            2. Disable Single Sign-On, SAML, Local Login then select skip updates
            3. Enable Single Sign-On then select skip updates
            4. Disable Single Sign-On then select skip updates
            5. Enable SAML then select skip updates
            6. Disable SAML then select skip updates
            7. Enable Local Login then select skip updates
            8. Disable Local Login then select skip updates
        expectedResults:
            1. check changes in ui
            2. check changes in ui
            3. check changes in ui
            4. check changes in ui
            5. check changes in ui
            6. check changes in ui
            7. check changes in ui
            8. check changes in ui
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_hot_vsphere65_nested_persistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_candu_collection_tab():
    """
    Test case to cover -
    https://bugzilla.redhat.com/show_bug.cgi?id=1393675
    from BZ comments:
    "for QE testing you can only replicate that in the UI by running a
    refresh and immediately destroying the provider and hope that it runs
    into this race conditions."

    Polarion:
        assignee: nachandr
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_self_service_ui_should_show_pending_requests():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1321352

    Polarion:
        assignee: sshveta
        casecomponent: ssui
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: SUI : Self Service Ui should show pending requests
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
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_current_server_all_unconfigured():
    """
    check collect logs under server when both levels are unconfigured.
    Expected result - all buttons are disabled

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_machine_credentials_vault():
    """
    Add vault password and test in the playbook that encrypted yml can be
    decrypted.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_machine_credentials_escalate_perm_sudo():
    """
    Allow user/admin to create/import credentials for machines which will
    be managed (may need to be split into multiple tests to cover
    -Machine, Network, Amazon Web Services, Rackspace, VMware vCenter, Red
    Hat Satellite 6, Red Hat CloudForms, Google Compute Engine, Microsoft
    Azure Classic, Microsoft Azure Resource Manager, OpenStack)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_machine_credentials_machine_root_pass():
    """
    Allow user/admin to create/import credentials for machines which will
    be managed (may need to be split into multiple tests to cover
    -Machine, Network, Amazon Web Services, Rackspace, VMware vCenter, Red
    Hat Satellite 6, Red Hat CloudForms, Google Compute Engine, Microsoft
    Azure Classic, Microsoft Azure Resource Manager, OpenStack)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_add_machine_credentials_machine_ssh_key():
    """
    Allow user/admin to create/import credentials for machines which will
    be managed (may need to be split into multiple tests to cover
    -Machine, Network, Amazon Web Services, Rackspace, VMware vCenter, Red
    Hat Satellite 6, Red Hat CloudForms, Google Compute Engine, Microsoft
    Azure Classic, Microsoft Azure Resource Manager, OpenStack)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1h
        startsin: 5.8
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_multi_domain_configuration_for_external_auth_ldaps():
    """
    Look for the steps/instructions at
    https://mojo.redhat.com/docs/DOC-1085797
    Verify appliance_console is updated with “External Auth: “ correctly.
    Verify appliance_console displays all the domains configured. Now it
    displays only one. There will be BZ.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: verify multi domain configuration for external auth ldaps
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_saml_verify_get_user_groups_from_external_authentication_httpd__option():
    """
    Enable “Get User Groups from External Authentication (httpd)” option.
    Verify “user groups from SAML server are updated correctly and user
    with correct groups can login. (retrieve groups option is not valid in
    case of SAML)

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/2h
        title: saml: Verify “Get User Groups from External Authentication (httpd)” option.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_rhi_overview():
    """
    Verify testing whehter issues related to systems are categorised or
    not

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.rep
def test_distributed_zone_mixed_infra():
    """
    Azure,AWS, and local infra

    Polarion:
        assignee: tpapaioa
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_creds_tag():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1526219
    RBAC - tag credentials and allow new user see just this credential.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/2h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
@pytest.mark.tier(1)
def test_config_manager_add_multiple_times_ansible_tower_243():
    """
    Try to add same Tower manager twice (use the same IP/hostname). It
    should fail and flash message should be displayed.

    Polarion:
        assignee: nachandr
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_external_auth_configuration_for_ldap_can_be_un_configured_using_appliance_cons():
    """
    Run command “appliance_console”
    Select option for “configure external authentication”
    Verify “IPA Client already configured on this Appliance, Un-Configure
    first?” is displayed
    Answer yes to continue with unconfigure process.
    Verify Database user login works fine upon external auth un configured
    and auth mode set to ‘Database’.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/3h
        title: Verify external auth configuration for ldap can be un
               configured using appliance_console
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(2)
def test_embed_tower_order_service_extra_vars():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1444831
    Execute playbook with extra variables which will be passed to Tower.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
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
        casecomponent: infra
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
        casecomponent: candu
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.cfme_tenancy
@pytest.mark.tier(1)
def test_cloud_tenant_crud_rhos():
    """
    1. Add RHOS provider and perform refresh
    2. Navigate to Compute -> Clouds -> Providers
    3. Click on RHOS provider which was added
    4. In the Relationships table click on Cloud Tenants
    5. Configuration ->Create Cloud tenant6. Edit created tenant
    7. Try to delete it

    Polarion:
        assignee: ndhandre
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_reports_manage_report_menu_accordion_with_users():
    """
    Steps:
    1. Create a new report called report01
    2. Create a new user under EvmGroup-super_administrator called
    testuser
    3. "Edit Report Menus" and add the report01 under EvmGroup-
    super_administrator"s Provisioning -> Activities
    4. Login using testuser and navigate to Reports
    5. No report01 is under Provisioning -> Activities
    BZ: 1535023

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_refresh_with_empty_iot_hub_azure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1495318
    "For QE, if it helps - to reproduce reliably create an IoT Hub in
    Azure (using free tier pricing is good enough):
    $ az iot hub create --name rmanes-iothub --resource-group iot_rg"
    1.Prepare env ^^
    2.Refresh provider

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_reconfigure_vm_vmware_sockets_multiple():
    """
    Test changing the cpu sockets of multiple vms at the same time.

    Polarion:
        assignee: sshveta
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -get new configured appliance
               -add vmware provider
               -provision 2 new vms
               -power off 1 vm
               -select both vms
               -configure-->reconfigure vm
               -increase/decrease counts
               -power on vm
               -check changes
        startsin: 5.6
        testSteps:
            1. Hot increase
            2. Hot Decrease
            3. Cold Increase
            4. Cold Decrease
            5. Hot + Cold Increase
            6. Hot + Cold Decrease
        expectedResults:
            1. Action should succeed
            2. Action should fail
            3. Action should succeed
            4. Action should succeed
            5. Action should succeed
            6. Action should Error
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
def test_ec2_tags_instances():
    """
    Requirement: Have an ec2 provider
    1) Create an instance with tag test:testing
    2) Refresh provider
    3) Go to summary of this instance and check whether there is
    test:testing in Labels field
    4) Delete that instance

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
@pytest.mark.tier(1)
def test_embed_tower_logs():
    """
    Separate log files should be generated for Ansible to aid debugging.
    p1 (/var/log/tower)

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
def test_pod_appliance_image_upgrade():
    """
    one of appliance images has been changed. it should cause pod re-
    deployment

    Polarion:
        assignee: izapolsk
        caseimportance: medium
        initialEstimate: None
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_zone_multiple_servers_zone_setup():
    """
    using any type of depot check collect all log function under zone.
    Zone should have multiplie servers under it. Zone should be setup,
    servers should not

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collection_usercase_multiple_servers_dropbox():
    """
    Polarion:
        assignee: anikifor
        casecomponent: config
        initialEstimate: 1/4h
        setup: Set servers into distributed mode t
        testSteps:
            1. Go to Configure/Configuration/Diagnostics
            2. With the cfme server selected go to Collect Logs and click on Edit
            3. Select Red Hat Dropbox for type and click Save in the bottom right hand corner.
            4. Go back to Configure/Configuration/Diagnostics/Collect Logs
               and collect all or current log
            5. Provide the support case number in the dialog that pops up.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Log file created with case number in the beginning
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
def test_custom_button_edit_via_rest_put():
    """
    Steps:
    1) Create custom button
    2) Use Put method to edit the custom button
    3) Delete custom button

    Polarion:
        assignee: ndhandre
        initialEstimate: None
        startsin: 5.9
    """
    pass


@pytest.mark.manual
def test_custom_button_edit_via_rest_patch():
    """
    Steps:
    1) Create Custom button
    2) Edit custom button using Patch method
    3) Delete custom button

    Polarion:
        assignee: ndhandre
        initialEstimate: None
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_infra_networking_switch():
    """
    Setup: Create group with tag, use this group for user creation
    1. Add tag(used in group) for infra networking switch via detail page
    2. Remove tag for infra networking switch via detail page
    3. Add tag for infra networking switch via list
    4. Check infra networking switch is visible for restricted user
    5. Remove tag for infra networking switch via list
    6 . Check infra networking switch isn"t visible for restricted user

    Polarion:
        assignee: anikifor
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.config_management
def test_config_manager_job_template_refresh():
    """
    After first Tower refresh, go to Tower UI and change name of 1 job
    template. Go back to CFME UI, perform refresh and check if job
    template name was changed.

    Polarion:
        assignee: nachandr
        casecomponent: ansible
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_generate_reports_after_upgrade():
    """
    Test generate reports after updating the appliance to release version
    from prior version.
    BZ LInk: 1464154

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.3
    """
    pass


@pytest.mark.manual
def test_custom_button_submit_ssui_all():
    """
    Test custom button all submit via SSUI

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_custom_button_submit_ssui_sequence():
    """
    Test custom button submit sequence via SSUI

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_custom_button_submit_ssui_both():
    """
    Test custom button display for detail and list page of SSUI

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
    """
    pass


@pytest.mark.manual
def test_custom_button_submit_ssui_list():
    """
    Test custom button display for list page for SSUI

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        upstream: yes
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
@test_requirements.service
@pytest.mark.tier(1)
def test_service_reconfigure_in_distributed_environment():
    """
    Create master and child appliance.
    raise provisioning request in master and reconfigure in child.

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Service Reconfigure in distributed environment
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
@test_requirements.ssui
@pytest.mark.tier(2)
def test_snapshot_timeline_verify_data():
    """
    Test the SUI snapshot timeline.
    See if data on the popup correspond to data shown below the timeline.

    Polarion:
        assignee: apagac
        casecomponent: infra
        caseimportance: low
        initialEstimate: 1/3h
        testSteps:
            1. create a new vm
            2. create a snapshot
            3. go to the VM details page, then Monitoring -> Timelines
            4. select "Management Events" and "Snapshot Activity" and click Apply
            5. click on the event, compare data from the popup with data
               shown below the timeline
        expectedResults:
            1. vm created
            2. snapshot created
            3. timelines page displayed
            4. event displayed on timeline
            5. data should be identical
    """
    pass


@pytest.mark.manual
def test_custom_button_simulation():
    """
    Test whether custom button works with simulation option
    (Additional info: https://bugzilla.redhat.com/show_bug.cgi?id=1535215)

    Polarion:
        assignee: ndhandre
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.8
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_cfme_features_with_ldap():
    """
    verifies the cfme features with authentication mode configured to
    ldap.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1h
        testSteps:
            1. login with ldap user
            2. verify the CFME features after login with ldap user.
        expectedResults:
            1. login should be successful
            2. All the CFME features should work properly with ldap authentication.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere67_rhel6x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (versions : latest to latest-2)
    vSphere: 65
    OS: RHEL 6.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create RHEL 6.x VM on vSphere55
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere67_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere65_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere6_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6
    OS: Fedora 28

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 28 VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere6_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for each version of Firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. You should see same result across all versions
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere65_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: critical
        initialEstimate: 1/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_edge_vsphere6_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Edge
    vSphere: 6
    OS: Windows 10

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/4h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere55_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere65_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6.5
    OS: fedora26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere67_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6.5
    OS: fedora26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere67_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (versions : latest to latest-2)
    vSphere: 65
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere65
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for all the firefox versions
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. you should see same results
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere55_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 5.5
    OS: fedora26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere55_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere6_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere 5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_novmrccredsinprovider():
    """
    Leave the VMRC Creds blank in the provider add/edit dialog and observe
    behavior trying to launch console. It should fail. Also observe the
    message in VMRC Console Creds tab about what will happen if creds left
    blank. https://bugzilla.redhat.com/show_bug.cgi?id=1550612

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: critical
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere55_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 5.5
    OS: fedora28

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 28 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere65_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6.5
    OS: Fedora 26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere6.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere65_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (versions : latest to latest-2)
    vSphere: 65
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere65
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for all the firefox versions
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. you should see same results
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere65_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere 5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere67_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: critical
        initialEstimate: 1/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere65_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6.5
    OS: Fedora 28

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 28 VM on vSphere6.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere65_rhel6x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (versions : latest to latest-2)
    vSphere: 65
    OS: RHEL 6.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create RHEL 6.x VM on vSphere55
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere6_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for each version of Firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. You should see same result across all versions
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere65_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere67_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6.5
    OS: Fedora 26

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere6.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere67_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere6_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6
    OS: fedora27

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 27 VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere6_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 6
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere67_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere67_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6.5
    OS: fedora26

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere65_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere 5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere65_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6.5
    OS: fedora28

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 28 VM on vSphere6.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere55_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_edge_vsphere67_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Edge
    vSphere: 65
    OS: Windows 10

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/4h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_edge_vsphere65_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Edge
    vSphere: 65
    OS: Windows 10

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/4h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere55_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 5.5
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere55_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 5.5
    OS: fedora27

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 27 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere67_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6.5
    OS: Fedora 26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere6.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere67_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere65_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere67_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere6_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6
    OS: Fedora 27

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 27 VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere67_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere 5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere65_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere67_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere67_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere 5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_addremovevmwarecreds():
    """
    Add VMware VMRC Console Credentials to a VMware Provider and then
    Remove it. As per BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1559957

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/4h
        startsin: 5.8
        testSteps:
            1. Compute->Infrastructure->Provider, Add VMware Provider with VMRC Console Creds
            2. Edit provider, remove VMware VMRC Console Creds and Save
        expectedResults:
            1. Provider added
            2. Provider can be Saved without VMRC Console Creds
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere65_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6.5
    OS: fedora27

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 27 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere55_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere55_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 5.5
    OS: Fedora 26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere67_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6.5
    OS: fedora26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere55_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 5.5
    OS: Fedora 27

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 27 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere55_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere6_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere65_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere65_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6.5
    OS: Fedora 25

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 25 VM on vSphere6.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere6_rhel6x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox
    vSphere: 6
    OS: RHEL 6.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create RHEL 6.x VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for all the firefox versions
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. you should see same results
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere6_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere6_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: critical
        initialEstimate: 1/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere65_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. repeat above steps for other versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be the same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere55_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (versions : latest to latest-2)
    vSphere: 55
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere55
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for all the firefox versions
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. you should see same results
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere6_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6
    OS: fedora26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere6_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 6
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere6_rhel7x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (versions : latest to latest-2)
    vSphere: 6
    OS: RHEL 7.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: critical
        initialEstimate: 1/3h
        setup: Steps:
               Create RHEL 7.x VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for all the firefox versions
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. you should see same results
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_edge_vsphere55_win10():
    """
    VMRC Console Testing in following Environment:
    Browser: Edge
    vSphere: 6
    OS: Windows 10

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/4h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere55_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 5.5
    OS: Fedora 27

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 27 VM on vSphere5.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere6_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (52,51,50) - Always take latest to latest-2 versions.
    vSphere: 6
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Windows 7 VM on vSphere6
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for each version of Firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. You should see same result across all versions
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere67_fedora27():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6.5
    OS: Fedora 26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 26 VM on vSphere6.5
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere55_win7():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere 5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_usecredwithlimitedvmrcaccess():
    """
    Add Provider in VMware now has a new VMRC Console Tab for adding
    credentials which will be used to initiate VMRC Connections and these
    credentials could be less privileged as compared to Admin user but
    needs to have Console Access.
    In current VMware env we have "user_interact@vsphere.local" for this
    purpose. It is setup on vSphere65(NVC) and has no permissions to add
    network device, suspend vm, install vmware tools or reconfigure
    floppy. So if you can see your VMRC Console can"t do these operations
    with user_interact, mark this test as passed. As the sole purpose of
    this test is to validate correct user and permissions are being used.
    https://bugzilla.redhat.com/show_bug.cgi?id=1479840

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: critical
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_firefox_vsphere55_rhel6x():
    """
    VMRC Console Testing in following Environment:
    Browser: Firefox (versions : latest to latest-2)
    vSphere: 55
    OS: RHEL 6.x

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create RHEL 6.x VM on vSphere55
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Get Firefox browser tar balls from the following URL:
               https://ftp.mozilla.org/pub/firefox/releases/
               Untar each and launch firefox from respective directories. (Technical
               Gotcha: Start with latest browser, so it will not auto-update before
               you change its update settings)
               Make sure the browser auto updates are also disabled
        testtype: integration
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "I understand Risks" then click "Add exception" and
               click "Confirm")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere55_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: Chrome
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome Browser latest version
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_ie11_vsphere55_win2012():
    """
    VMRC Console Testing in following Environment:
    Browser: IE11
    vSphere: 5.5
    OS: Windows 7

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: Steps:
               Create Windows 7 VM on vSphere 5.5
               Disable Automatic updates for OS
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on IE11
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_chrome_vsphere6_fedora28():
    """
    VMRC Console Testing in following Environment:
    Browser: chrome-latest
    vSphere: 6
    OS: fedora28

    Polarion:
        assignee: apagac
        casecomponent: appl
        initialEstimate: 1/3h
        setup: Steps:
               Create Fedora 28 VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               Install Chrome
               Make sure the browser auto updates are also disabled
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
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
def test_vmrc_console_firefox_vsphere6_fedora26():
    """
    VMRC Console Testing in following Environment:
    Browser: firefox
    vSphere: 6
    OS: Fedora 26

    Polarion:
        assignee: apagac
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 2/3h
        setup: Steps:
               Create Fedora 25 VM on vSphere6
               Install VMRC Plugin (Ask mpusater on IRC for the setup file)
               All Firefox versions can be found at following address:
               https://ftp.mozilla.org/pub/firefox/releases/
               Make sure the browser auto updates are also disabled
        testSteps:
            1. Launch CFME Appliance on Firefox
            2. Go to Compute->Infrastructure->Virtual Machines
            3. Click on any of the running/powered on VMs
            4. On top of details, Click on Access->Select VM Console from Dropdown
            5. Repeat above steps for other 2 versions of firefox
        expectedResults:
            1. CFME Appliance Login page should be displayed (Might warn
               you about certificate/trust please proceed by accepting
               (Click "Continue to this website (not Recommended)")
            2. Should see list of Available VMs by all providers
            3. Should see a details page containing detailed info about that VM
            4. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            5. results should be same
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_all():
    """
    Test enabling/disabling all ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: config
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
@test_requirements.service
@pytest.mark.tier(3)
def test_second_dialog_dynamic_element_should_be_able_to_read_the_previous_textbox_element():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1576107 Steps to
    Reproduce:
    1. import example automate domain
    2. import example service dialog
    3. create a generic catalog item with the dialog service dialog
    provided

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Second dialog dynamic element should be able to read the
               previous textbox element
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_configuration_displayed_navigation_pane():
    """
    Go to Configuration -> Settings
    1) CFME Region - no navigation pane
    1a) C & U Collection - no navigation pane
    1b) Tags -> My Company Categories/My Company Tags/ Import Tags/Import
    Variables/Map Tags - no navigation pane
    1c) Red Hat Updates - no navigation pane
    1d) Help Menu - no navigation pane
    2) Analysis Profiles - pagination pane
    2a) sample analysis profile - no pagination pane
    3) Zones - no navigation pane
    3a) Default zone -> Zone/SmartProxy Affinity - no pagination pane
    4) Server - no navigation pane
    4a) Authentication - no navigation pane
    4b) Workers - no navigation pane
    4c) Custom Logos - no navigation pane
    4d) Advanced - no navigation pane
    5) Schedules - navigation pane
    5a) Create a schedule -> Schedules - navigation pane
    5b) Single schedule - no navigation pane
    Go to Configuration -> Access Control
    1) CFME Region - no navigation pane
    1a) Users - navigation pane
    2b) Single user - no navigation pane
    2c) Groups - navigation pane
    2d) Single group - no navigation pane
    2e) Roles - navigation pane
    2f) Single role - no navigation pane
    2g) Tenant - navigation pane
    2h) Single tenant - no navigation pane
    Go to Configuration -> Diagnostics
    1) CFME Region - no navigation pane
    1a) Roles by Servers - no navigation pane
    1b) Servers by Roles - no navigation pane
    1c) Servers - no navigation pane
    1d) Database - no navigation pane
    1e) Orphaned data - no navigation pane
    2) Zone - no navigation pane
    2a) Servers by Roles - no navigation pane
    2b) Servers - no navigation pane
    2c) Collect logs - no navigation pane
    2d) C & U Gap Collection - no navigation pane
    3) Server - no navigation pane
    3a) Workers - no navigation pane
    3b) Collect Logs - no navigation pane
    3c) CFME Log - no navigation pane
    3d) Audit Log - no navigation pane
    3e) Production Log - no navigation pane
    3f) Utilization - no navigation pane
    3g) Timelines - no navigation pane
    4) Go to Configuration -> Database - no pagination pane
    4a) Tables - pagination pane
    4b) Indexes - pagination pane
    4c) Settings - pagination pane
    4d) Client Connections - pagination pane
    4e) Utilization - no pagination pane

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_username_fields_error_azure():
    """
    1.Provision Azure Instance
    2.Use "admin" as username / "password" as password
    3.Verify that we have Error Flash messages for both fields

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_cockpit_button_disabled_on_windows_vms():
    """
    Cockpit is a Linux only solution.  Talked with UI team and they wanted
    a bug to make sure Access\Web Console is disabled for Windows VMs
    https://bugzilla.redhat.com/show_bug.cgi?id=1447100

    Polarion:
        assignee: sshveta
        casecomponent: web_ui
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
        setup: You need to select a Windows VM that is both running and has an IP
               address assigned to it.  When fixed, the Access \ Web Console menu
               item should be deleted.
        startsin: 5.8
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_verify_benchmark_timings_are_correct():
    """
    Bug 1424716 - Benchmark timings are incorrect for all workers in
    evm.log
    https://bugzilla.redhat.com/show_bug.cgi?id=1424716
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

    Polarion:
        assignee: tpapaioa
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        title: Verify benchmark timings are correct
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_retire_on_date_for_multiple_service():
    """
    Retire on date for multiple service

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
        title: Retire on date for multiple service
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_order_service_after_deleting_provider():
    """
    Order service

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: Order service after deleting provider
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
        casecomponent: web_ui
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
@test_requirements.general_ui
def test_configuration_start_page_menu_category():
    """
    Navigate to Settings -> My Settings
    List through Start Page - Show at Login select menu and check whether
    Items have right menu category.
    Like Cloud Intel / Dashboard means that Dashboard page is in Cloud
    Intel menu.

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.smartstate
@pytest.mark.tier(1)
def test_ssa_vm_files():
    """
    Check file list is fetched correctly for analysed VM

    Polarion:
        assignee: sbulage
        casecomponent: smartst
        caseimportance: medium
        initialEstimate: 1/2h
        testtype: integration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_restrict_domain_crud():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1365493
    When you create a role that can only view automate domains, it can
    view automate domains, it cannot manipulate the domains themselves,
    but can CRUD on namespaces, classes, instances ....

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_vm_migrate_should_create_notifications_when_migrations_fail():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1478462

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        title: VM Migrate should create notifications  when migrations fail.
    """
    pass


@pytest.mark.manual
@test_requirements.cloud_init
@pytest.mark.tier(1)
def test_cloud_init_with_cfme():
    """
    test cloud init payload with latest cfme image

    Polarion:
        assignee: None
        casecomponent: appl
        endsin: 5.4
        initialEstimate: 1/2h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_remote_server_advanced_config():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1536524

    Polarion:
        assignee: anikifor
        casecomponent: config
        initialEstimate: 1/4h
        startsin: 5.10
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_notification_notification_about_new_cfme_appliance_update_to_the_admin():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/4h
        title: Notification : Notification about new cfme-appliance update to the admin
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_regions_gov_azure():
    """
    This test verifies that Azure Government regions are not included in
    the default region list as most users will receive errors if they try
    to use them.
    https://bugzilla.redhat.com/show_bug.cgi?id=1412363

    Polarion:
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        setup: Check the region list when adding a Azure Provider.
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_performance_reports():
    """
    1. Create role with group and user restriction
    2. Create groups with tag
    3. Create user with selected group
    4. Set the group ownership and tag for one of VMs
    5. Generate performance report
    6. As user add widget to dashboard
    7. Check widget content -> User should see only one vm with set
    ownership and tag

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_create_remove_network_security_groups_events_azure():
    """
    create/remove network security groups events[azure]

    Polarion:
        assignee: None
        caseimportance: low
        initialEstimate: 1/4h
        title: create/remove network security groups events[azure]
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_zone_multiple_servers():
    """
    using any type of depot check collect all log function under zone.
    Zone should have multiplie servers under it. Zone and all servers
    should have their own settings

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.report
@pytest.mark.tier(1)
def test_queue_tenant_quotas_report():
    """
    Test multiple possible Tenant Quota Report configurations

    Polarion:
        assignee: pvala
        casecomponent: report
        initialEstimate: 1/4h
        setup: Create or Identify appliance with one or more synced providers
        title: Queue Tenant Quotas Report
        testSteps:
            1. Sign in to appliance
            2. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            3. Turn on Allocated Virtual CPUs and set it up to 10
            4. Save new quota configuration
            5. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            6. Queue Tenant Quotas report
            7. //Wait ~1 minute
            8.
            9.
            10. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            11. Turn off Allocated Virtual CPUs, turn on Allocated Memory in
                GB and set it up to 100
            12. Save new quota configuration
            13. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            14. Queue Tenant Quotas report
            15. //Wait ~1 minute
            16.
            17.
            18. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            19. Turn on Allocated Virtual CPUs and set it up to 10, turn on
                Allocated Memory in GB and set it up to 100
            20. Save new quota configuration
            21. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            22. Queue Tenant Quotas report
            23. //Wait ~1 minute
            24.
            25.
            26. Navigate to Settings > Access control > Tenants > My Tenant > Manage quotas
            27. Turn on all quotas and set them up adequate numbers
            28. Save new quota configuration
            29. Navigate to Cloud Intel > Reports > Reports > Tentant Quotas
            30. Queue Tenant Quotas report
            31. //Wait ~1 minute
            32.
            33.
            34. Sign out
        expectedResults:
            1.
            2.
            3.
            4. Verify that flash message "Quotas for Tenant were saved" is shown
            5.
            6.
            7. Verify that only Allocated Virtual CPUs row is present in report
            8. Verify that Count is unit in the report
            9. Verify that following columns are shown in report:
               Tenant Name         Quota Name         Total Quota
               In Use         Allocated         Available
            10.
            11.
            12. Verify that flash message "Quotas for Tenant were saved" is shown
            13.
            14.
            15. Verify that only Allocated Memory in GB row is present in report
            16. Verify that GB is unit in the report
            17. Verify that following columns are shown in report:
                Tenant Name         Quota Name         Total Quota
                In Use         Allocated         Available
            18.
            19.
            20. Verify that flash message "Quotas for Tenant were saved" is shown
            21.
            22.
            23. Verify that Allocated Virtual CPUs and Allocated Memory in
                GB rows are present in report
            24. Verify that both Count and GB units are used in the report
            25. Verify that following columns are shown in report:
                Tenant Name         Quota Name         Total Quota
                In Use         Allocated         Available
            26.
            27.
            28. Verify that flash message "Quotas for Tenant were saved" is shown
            29.
            30.
            31. Verify that all quotas are present in report
            32. Verify that both Count and GB units are used in the report
            33. Verify that following columns are shown in report:
                Tenant Name         Quota Name         Total Quota
                In Use         Allocated         Available
            34.
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_vm_reconfig_resize_disk_cold_vsphere67_nested_persistent_thick():
    """
    Polarion:
        assignee: nansari
        casecomponent: infra
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_edit_log_collection_spinner_present():
    """
    Check that spinner present in "edit log depot" page.

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_configure_ldaps_for_customized_port_eg_10636_10389_and_validate_cfme_auth():
    """
    Configure ldap/ldaps domain server with customized port.
    Configure cfme for customized domain ports. Check mojo page for
    details.
    Verify ldap user/group authentication.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/2h
        title: Configure  ldaps for customized port e.g 10636, 10389 and validate CFME auth
    """
    pass


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(3)
def test_sui_request_explorer_will_show_all_status_of_requests():
    """
    desc

    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.8
        title: SUI: Request explorer will show all status of requests
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_user_should_be_able_to_change_the_order_of_values_of_the_drop_down_list():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1594301

    Polarion:
        assignee: nansari
        initialEstimate: 1/16h
        startsin: 5.10
        title: User should be able to change the order of values of the drop down list
    """
    pass


@pytest.mark.manual
@test_requirements.log_depot
@pytest.mark.tier(1)
def test_log_collect_all_zone_zone_setup():
    """
    using any type of depot check collect all log function under zone
    (settings under server should not be configured, under zone should be
    configured)

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.reconfigure
@pytest.mark.tier(1)
def test_reconfigure_vm_vmware_mem_multiple():
    """
    Test changing the memory of multiple vms at the same time.

    Polarion:
        assignee: sshveta
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -get new configured appliance
               -add vmware provider
               -provision 2 new vms
               -power off 1 vm
               -select both vms
               -configure-->reconfigure vm
               -increase/decrease counts
               -power on vm
               -check changes
        startsin: 5.6
        testSteps:
            1. Hot increase
            2. Hot Decrease
            3. Cold Increase
            4. Cold Decrease
            5. Hot + Cold Increase
            6. Hot + Cold Decrease
        expectedResults:
            1. Action should succeed
            2. Action should fail
            3. Action should succeed
            4. Action should succeed
            5. Action should succeed
            6. Action should Error
    """
    pass


@pytest.mark.manual
@test_requirements.ansible
def test_embed_tower_exec_play_against_ipv6_machine():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against machine which has ipv6 address.

    Polarion:
        assignee: sbulage
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
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
        casecomponent: candu
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
        casecomponent: candu
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
        casecomponent: candu
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(3)
def test_check_required_button_on_all_dialog_elements():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1512398
    Steps to Reproduce:
    1. Create a dialog with some entries and "required" button turned ON.
    2. Create a catalog item that uses this dialog.
    3. When we order that catalog item the order is submitted without
    selecting any item in the dropdown.

    Polarion:
        assignee: sshveta
        casecomponent: services
        initialEstimate: 1/4h
        title: Check "Required" button on all dialog elements
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
@pytest.mark.tier(1)
def test_custom_button_visibility():
    """
    This test is required to test the visibility option in the customize
    button.
    Steps
    1)Create Button Group
    2)Create a Button for the button group
    3)Add the Button group to a page
    4)Make write a positive visibility expression
    5)If button is visible and clickable then pass else fail

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_saml_verify_multiple_appliances_can_be_added_to_the_same_realm():
    """
    Verify configuring more than one appliance to SAML authentication as
    mentioned in Step#1 works fine.

    Polarion:
        assignee: apagac
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
        title: saml: Verify multiple appliances can be added to the same REALM.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_embedded_method():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1523379
    For a "new" method when adding Embedded Methods the UI hangs in the
    tree view when the method is selected

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/12h
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
        assignee: None
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/5h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_cfme_login_page_redirects_to_saml_login_page_upon_successful_configuration():
    """
    click on login to corporate account if local login is enabled,
    redirects to SAML REALM page for which user is appliance is configured
    to.

    Polarion:
        assignee: apagac
        casecomponent: config
        initialEstimate: 1/4h
        title: Verify CFME login page redirects to SAML login page upon
               successful configuration
    """
    pass


@pytest.mark.manual
def test_search_field_at_the_top_of_a_dynamic_drop_down_dialog_element_should_display():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1553347

    Polarion:
        assignee: nansari
        casecomponent: services
        initialEstimate: 1/4h
        startsin: 5.9
        title: search field at the top of a dynamic drop-down dialog element should display
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_git_verify_ssl():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1470738

    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/12h
        startsin: 5.7
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
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_host_info_scvmm2016():
    """
    The purpose of this test is to verify that SCVMM-2016 hosts are not
    only added, but that the host information details are correct.  Take
    the time to spot check at least one host.

    Polarion:
        assignee: None
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass
