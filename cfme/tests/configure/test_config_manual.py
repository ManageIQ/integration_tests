# -*- coding: utf-8 -*-
"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.settings
@pytest.mark.tier(3)
def test_validate_landing_pages_for_rbac():
    """
    Bugzilla:
        1450012

    Polarion:
        assignee: pvala
        casecomponent: Settings
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


@pytest.mark.manual
@test_requirements.settings
@pytest.mark.tier(1)
def test_my_settings_default_views_alignment():
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/20h
        testSteps:
            1. Go to My Settings -> Default Views
        expectedResults:
            1. All icons are aligned correctly
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_configure_icons_roles_by_server():
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
        testSteps:
            1. Go to Settings -> Configuration and enable all Server Roles.
            2.Navigate to Settings -> Configuration -> Diagnostics -> CFME Region ->
            Roles by Servers.
            3. Click through all Roles and look for missing icons.
        expectedResults:
            1.
            2.
            3. No icons are missing
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_verify_page_landing_cloud_subnets():
    """
    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/10h
        startsin: 5.6
        testSteps:
            1. Navigate to compute-> cloud -> instance -> click on any instance ->
            Click on Cloud Networks (under relationships)
            2. Check if the page is displayed.
        expectedResults:
            1.
            2. Page must be displayed correctly.
    """
    pass
