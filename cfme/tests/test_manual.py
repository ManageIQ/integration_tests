# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream('5.10', 'upstream')]


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
