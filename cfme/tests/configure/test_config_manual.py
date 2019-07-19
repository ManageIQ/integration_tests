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
@test_requirements.general_ui
@pytest.mark.meta(coverage=[1715466, 1455283, 1404280])
@pytest.mark.tier(1)
def test_configuration_dropdown_roles_by_server():
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: high
        initialEstimate: 1/15h
        testSteps:
            1. Navigate to Settings -> Configuration -> Diagnostics -> CFME Region ->
                Roles by Servers.
            2. Select a Role and check the `Configuration` dropdown in toolbar.
            3. Check the `Suspend Role` option.
            4. Click the `Suspend Role` option and suspend the role
                and monitor production.log for error -
                `Error caught: [ActiveRecord::RecordNotFound] Couldn't find MiqServer with 'id'=0`
        expectedResults:
            1.
            2. `Configuration` dropdown must be enabled/active.
            3. `Suspend Role` must be enabled.
            4. Role must be suspended and there must be no error in the logs.

    Bugzilla:
        1715466
        1455283
        1404280
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1498090])
def test_diagnostics_server():
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/15h
        testSteps:
            1. Navigate to Configuration and go to Diagnostics accordion.
            2. Click on Region.
            3. Click on `Servers` tab and select a server from the table and check the landing page.
            4. Click Zone.
            5. Click on `Servers` tab and select a server from the table and check the landing page.
        expectedResults:
            1.
            2.
            3. Landing page must be `Diagnostics Server` summary page.
            4.
            5. Landing page must be `Diagnostics Server` summary page.

    Bugzilla:
        1498090
    """
    pass
