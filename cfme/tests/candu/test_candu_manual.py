"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.manual,
]


@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_datastore():
    """
    Verify bottleneck events from host

    Polarion:
        assignee: gtalreja
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: functional
    """
    pass


@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_provider():
    """
    Verify bottleneck events from providers

    Polarion:
        assignee: gtalreja
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: functional
    """
    pass


@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_host():
    """
    Verify bottleneck events from host

    Polarion:
        assignee: gtalreja
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: functional
    """
    pass


@test_requirements.bottleneck
@pytest.mark.tier(2)
def test_bottleneck_cluster():
    """
    Verify bottleneck events from cluster

    Polarion:
        assignee: gtalreja
        casecomponent: Optimize
        caseimportance: medium
        initialEstimate: 3/4h
        testtype: functional
    """
    pass


@test_requirements.bottleneck
@pytest.mark.tier(1)
def test_bottleneck_summary_graph():
    """
    test_bottleneck_summary_graph

    Polarion:
        assignee: gtalreja
        casecomponent: Optimize
        initialEstimate: 1/4h
        testSteps:
            1. setup c&u for provider and wait for bottleneck events
        expectedResults:
            1. summary graph is present and clickeble
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
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
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(2)
@test_requirements.c_and_u
def test_crosshair_op_azone_azure():
    """
    Utilization Test

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(2)
@test_requirements.c_and_u
def test_crosshair_op_azone_ec2():
    """
    test_crosshair_op_azone[ec2]

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: functional
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_host_tagged_crosshair_op_vsphere65():
    """
    Required C&U enabled application:1. Navigate to host C&U graphs
    2. select Group by option with suitable VM tag
    3. try to drill graph for VM

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_cluster_graph_by_vm_tag_vsphere65():
    """
    test_cluster_graph_by_vm_tag[vsphere65]

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_cluster_graph_by_host_tag_vsphere65():
    """
    test_cluster_graph_by_host_tag[vsphere65]

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_candu_graphs_vm_compare_host_vsphere65():
    """
    test_candu_graphs_vm_compare_host[vsphere65]

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_candu_graphs_vm_compare_cluster_vsphere65():
    """
    test_candu_graphs_vm_compare_cluster[vsphere65]

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
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
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(2)
@test_requirements.c_and_u
def test_crosshair_op_instance_azure():
    """
    Utilization Test

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(2)
@test_requirements.c_and_u
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
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: functional
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
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
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_group_by_tag_azone_azure():
    """
    Utilization Test

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_azone_group_by_tag_ec2():
    """
    test_azone_group_by_tag[ec2]

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
        testtype: functional
    """
    pass


@pytest.mark.tier(2)
@test_requirements.c_and_u
def test_candu_graphs_datastore_vsphere6():
    """
    test_candu_graphs_datastore[vsphere6]

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
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
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
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
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_cluster_tagged_crosshair_op_vsphere65():
    """
    Required C&U enabled application:1. Navigate to cluster C&U graphs
    2. select Group by option with suitable VM/Host tag
    3. try to drill graph for VM/Host

    Polarion:
        assignee: gtalreja
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
def test_ec2_instance_memory_metrics():
    """
        Bugzilla:
            1684525

        Polarion:
            assignee: gtalreja
            casecomponent: Cloud
            initialEstimate: 1h
            caseimportance: medium
            casecomponent: CandU
            testSteps:
                1. Setup EC2 instance with CloudWatch Metrics Agent(https://docs.aws.amazon.com/
                AmazonCloudWatch/latest/monitoring/metrics-collected-by-CloudWatch-agent.html)
                2. Enable Memory metrics
                3. Add EC2 Provider to CFME
                4. Wait at least 30 minutes
                5. Go to Compute -> Cloud -> Instances
                6. Select instance with CloudWatch Metrics Agent
                7. Go to its memory metrics.
            expectedResults:
                1.
                2.
                3.
                4.
                5.
                6.
                7. Memory metrics should have data.
    """
    pass


@pytest.mark.tier(3)
@test_requirements.c_and_u
@pytest.mark.meta(coverage=[1776684])
def test_candu_verify_global_utilization_metrics():
    """
        Bugzilla:
            1776684

        Polarion:
            assignee: gtalreja
            casecomponent: CandU
            initialEstimate: 1h
            caseimportance: medium
            startsin: 5.10
            testSteps:
                1. Set up replication with 2 appliances global and remote
                2. Enable C&U data on both appliances
                3. Add provider on the remote, check data on the provider's dashboard
                4. Add same provider on the global, check data on the provider's dashboard
                5. Wait for at least 1 day for "Global Utilization" tab for providers
            expectedResults:
                1.
                2.
                3.
                4.
                5. Metrics should be same for Global and Remote regions.
    """
    pass
