# -*- coding: utf-8 -*-
"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.discovery
@pytest.mark.tier(1)
def test_infrastructure_providers_rhevm_edit_provider_no_default_port():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
        setup:
            1. Navigate to Compute > Infrastructure > Providers.
            2. Click on `Configuration` and select `Add a new Infrastructure provider`.
            3. Add a rhevm provider.
            4. Edit it and try to change it to another rhevm provider.
        testSteps:
            1. There shouldn't be any default API port.
        expectedResults:
            1. API port should be blank.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@test_requirements.discovery
def test_add_infra_provider_screen():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        setup:
            1. Navigate to Compute > Infrastructure > Providers.
            2. Click on `Configuration` and select `Add a new Infrastructure provider`.
        testSteps:
            1. test form validation using incorrect format for each field
            2. test wrong ip
            3. test wrong credentials
            4. test wrong security protocol
            5. test wrong provider type
        expectedResults:
            1. Form must not be validated.
            2. Form must not be validated.
            3. Form must not be validated.
            4. Form must not be validated.
            5. Form must not be validated.
    """
    pass


@test_requirements.general_ui
@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1532404])
def test_provider_summary_topology():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/2h
        setup:
            1. Add an infra provider.
        testSteps:
            1. Navigate to provider's summary page.
            2. Click on topology.
        expectedResults:
            1.
            2. Provider Topology must be displayed.

    Bugzilla:
        1532404
    """
    pass
