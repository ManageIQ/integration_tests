# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""

import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream("5.9", "5.10", "upstream")]


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
        casecomponent: rest
        initialEstimate: None
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_rest_metric_rollups():
    """
    This test checks that the we get a correct reply for our query.

    Polarion:
        assignee: pvala
        casecomponent: rest
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass
