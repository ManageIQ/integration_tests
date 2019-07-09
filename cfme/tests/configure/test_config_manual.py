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
@pytest.mark.tier(1)
def test_configuration_dropdown_roles_by_server():
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
        testSteps:
            1. Navigate to Settings -> Configuration -> Diagnostics -> CFME Region ->
                Roles by Servers.
            2. Select a Role and check the `Configuration` dropdown in toolbar.
            3. Check the `Suspend Role` option.
        expectedResults:
            1.
            2. `Configuration` dropdown must be enabled/active.
            3. `Suspend Role` must be enabled.

    Bugzilla:
        1715466
        1455283
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_replication_subscription_crud():
    """
    Add/Edit/Remove replication subscription

    Polarion:
        assignee: izapolsk
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_add_duplicate_subscription():
    """
    Try adding duplicate record

    Polarion:
        assignee: izapolsk
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_add_bad_subscription():
    """
    Try adding wrong subscriptions like
      1. remote appliance does have remote replication type set
      2. remote appliance isn't available and etc

    Polarion:
        assignee: izapolsk
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_edit_bad_subscription():
    """
    Try changing subscriptions from good to bad or vise versa

    Polarion:
        assignee: izapolsk
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_cancel_subscription():
    """
    Try canceling adding/changing/removing subscriptions

    Polarion:
        assignee: izapolsk
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_change_subscription_type():
    """
    Try setting/removing global subscription

    Polarion:
        assignee: izapolsk
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_subscription_disruption():
    """
    Test restoring subscription after temporary disruptions

    Polarion:
        assignee: izapolsk
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass
