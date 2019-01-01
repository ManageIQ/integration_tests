# -*- coding: utf-8 -*-
"""Manual tests"""

import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream("5.9", "5.10", "upstream")]


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_cloud_volume_types():
    """
    Test CloudVolumeType endpoint. Add a cloud provider and check if it
    gives correct response for the GET request.
    GET /api/cloud_volume_types
    GET /api/cloud_volume_types/:id
    PR: https://github.com/ManageIQ/manageiq-api/pull/465

    Polarion:
        assignee: pvala
        casecomponent: None
        caseimportance: high
        initialEstimate: 1/30h
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_rest_metric_rollups():
    """
    This test checks that the we get a correct reply for our query.

    Polarion:
        assignee: pvala
        casecomponent: None
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass
