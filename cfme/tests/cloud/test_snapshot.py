import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider


@pytest.mark.manual
@pytest.mark.provider([OpenStackProvider])
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_osp_snapshot_buttons():
    """
    Test new OSP snapshot button and make sure Snapshot link is removed from Instance Details
    page.

    Polarion:
        assignee: apagac
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.10
        setup:
            1. Have OSP provider added and test instance created
        testSteps:
            1. Navigate to test instance
            2. Make sure the snapshot button is displayed in the top menu
            3. Try snapshot crud
            4. Navigate to instance summary screen; Check if the original Snapshot link is present
        expectedResults:
            1. Test instance summary page displayed
            2. Snapshot button displayed
            3. Snapshot created; Snapshot deleted
            4. Snapshot link is not displayed
    Bugzilla:
        1690954
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([OpenStackProvider])
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_rhos_notification_for_snapshot_failures():
    """
    Test if cfme can report failure when deleting or creating
    snapshot on RHOS.

    Polarion:
        assignee: apagac
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/4h
        setup:
            1. Add RHOS provider
            2. Create a test VM on RHOS provider
        testSteps:
            1. Try to introduce a failure while creating snapshot
                * Delete the VM in the process of creating a snapshot
            2. Try to introduce a failure while deleting snapshot
                * Disconnect machine from network and then try to delete snapshot
        expectedResults:
            1. Notification for failure when creating the snapshot appears
            2. Notification for failure when deleting the snapshot appears
    Bugzilla:
        1581793

    """
    pass


@pytest.mark.manual
@pytest.mark.provider([OpenStackProvider])
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_notification_for_snapshot_actions_on_openstack():
    """
    Test task notification for snapshot tasks: success of create
    and delete snapshot.

    Polarion:
        assignee: apagac
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Add RHOS provider
            2. Create a test VM on RHOS provider
        testSteps:
            1. Create a snapshot
            2. Delete the snapshot
        expectedResults:
            1. Snapshot created successfully; notification displayed
            2. Snapshot deleted successfully; notification displayed
    Bugzilla:
        1429313
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([EC2Provider])
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_notification_for_snapshot_delete_failure_ec2():
    """
    Requires ec2 access via web-ui.

    Polarion:
        assignee: apagac
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/4h
        setup:
            1. Add ec2 provider
        testSteps:
            1. Create a snapshot on EC2 provider
            2. Try to delete snapshot via CFME UI
        expectedResults:
            1. Snapshot created
            2. Snapshot not deleted and notification displayed
    Bugzilla:
        1449243
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([OpenStackProvider])
@test_requirements.snapshot
@pytest.mark.meta(coverage=[1685300, 1703074, 1704340])
@pytest.mark.tier(2)
def test_snapshot_cloud_tenant():
    """
    Verify that snapshot created on an instance belonging to a non-admin tenant also belongs
    to the same non-admin tenant.

    Polarion:
        assignee: apagac
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/4h
        startsin: 5.10
        setup:
            1. Have OSP provider added
            2. Have non-admin cloud tenant created
            3. Deploy a new instance with non-admin cloud tenant
        testSteps:
            1. Create snapshot on newly deployed instance
            2. Navigate Compute -> Cloud -> Tenants -> <your tenant> -> Images
            3. Verify the snapshot is displayed here
            4. Navigate Compute -> Cloud -> Tenants -> admin -> Images
            5. Verify the snapshot is NOT displayed here
        expectedResults:
            1. Snapshot created
            2. Navigation successful
            3. Snapshot displayed for non-admin tenant
            4. Navigation successful
            5. Snapshot NOT displayed for admin tenant
    Bugzilla:
        1685300
    """
    pass
