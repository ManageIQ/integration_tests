# -*- coding: utf-8 -*-
"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.ignore_stream("5.9")
@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_cloud_volume_types():
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/30h
        startsin: 5.10
        setup:
            1. Add a cloud provider to the appliance.
        testSteps:
            1. Send GET request: /api/cloud_volume_types/:id
        expectedResults:
            1. Successful 200 OK response.
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_rest_metric_rollups():
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/10h
        setup:
            1. Add a provider to the appliance.
            2. Enable C&U on the appliance.
            3. Wait for few minutes.
        testSteps:
            1. Send GET request:
            /api/vms/:id/metric_rollups?capture_interval=hourly&start_date=':today_date'
        expectedResults:
            1. Successful 200 OK response.
    """
    pass
