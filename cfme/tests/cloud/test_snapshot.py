# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
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
