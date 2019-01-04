# -*- coding: utf-8 -*-
"""Manual tests"""

import pytest

from cfme import test_requirements


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
        setup:
            1. Create a new role by selecting a few product features.
            2. Create a group with the new role.
            3. Create a new user with the new group.
            4. Logout.
            5. Login back with the new user.
            6. Navigate to My Settings > Visual.
        testSteps:
            1.Check the start page entries in `Show at login` dropdown list
        expectedResults:
            1. Landing pages which user has access to must be present in the dropdown list.
    """
    pass
