# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream('5.10', '5.11', 'upstream')]


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
        testtype: functional
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
        assignee: jhenner
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
        assignee: jhenner
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
def test_orchestration_link_mismatch():
    """

    Bugzilla:
        1601523

    Polarion:
        assignee: sshveta
        casecomponent: Stack
        caseimportance: medium
        initialEstimate: 1/4h
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
        testtype: functional
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
