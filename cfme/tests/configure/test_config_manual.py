# -*- coding: utf-8 -*-
"""Manual tests"""

import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream("5.9", "5.10", "upstream")]


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
        testSteps:
            1.create a new role by selecting few product features.
            2.create a group base on the above role and the create a new
              user with this group
            3.Login with the new user and navigate
              to my settings->visuals and check the start page entries in
              show at login drop down list
        expectedResults:
            1. Display landing pages for which the user has access to
    """
    pass
