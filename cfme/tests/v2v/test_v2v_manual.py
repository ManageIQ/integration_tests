"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [test_requirements.v2v, pytest.mark.manual]


@pytest.mark.tier(1)
def test_vm_migration_from_iscsi_storage_in_vmware_to_iscsi_on_osp():
    """
    title: OSP: vmware67-Test VM migration from iSCSI Storage in VMware to iSCSI on OSP
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
            1. Create infrastructure mapping for vmware67 iscsi to OSP iscsi
            2. Create migration plan with infra map
            3. Start migration
        expectedResults:
            1.
            2.
            3. Successful migration from vmware to OSP
    """
    pass


@pytest.mark.tier(1)
def test_osp_vmware65_test_vm_migration_with_rhel_75():
    """
        title: OSP: vmware65-Test VM migration with RHEL 7.5
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
                1. Create infrastructure mapping for vmware65 iscsi to OSP
                2. Create migration plan with infra map and choose rhel75 VM
                3. Start migration
            expectedResults:
                1.
                2.
                3. Successful migration from vmware65 to OSP
        """
    pass


