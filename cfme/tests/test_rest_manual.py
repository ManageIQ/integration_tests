# -*- coding: utf-8 -*-
"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_create_rhev_provider_with_metric():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/10h
        testSteps:
            1. Add rhv provider with metrics via REST
        expectedResults:
            1. Provider must be added with all the details provided.
                In this case metric data. no data should be missing.

    Bugzilla:
        1656502
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_custom_logos_via_api():
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
        setup:
            1. Navigate to Configuration > Server > Custom Logos
            2. Change the brand, logo, login_logo and favicon
        testSteps:
            1.  Send a GET request: /api/product_info
        expectedResults:
            1. Response: {
                "name": "ManageIQ",
                "name_full": "ManageIQ",
                "copyright": "Copyright (c) 2019 ManageIQ. Sponsored by Red Hat Inc.",
                "support_website": "http://www.manageiq.org",
                "support_website_text": "ManageIQ.org",
                "branding_info": {
                    "brand": "/upload/custom_brand.png",
                    "logo": "/upload/custom_logo.png",
                    "login_logo": "/upload/custom_login_logo.png",
                    "favicon": "/upload/custom_favicon.ico"
                }
            }

    Bugzilla:
        1578076
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_tenant_parent_name_rest():
    """
    When you change the main parent tenant"s name that change is not
    reflected in api calls

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        upstream: yes
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_automation_request_task():
    """
    In this test we will try to edit a automation request using POST
    request.
    Note: Only Option field can be edited

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_edit_provider_request_task():
    """
    In this test we will try to edit a provider request using POST
    request.
    Note: Only Option field can be edited

    Polarion:
        assignee: pvala
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Rest
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_provider_specific_vm():
    """
    Steps:
    1) Add multiple provider
    2) Check for the vms specific to a provider
    2) Repeat it for all the providers

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_edit_request_task():
    """
    In this test we will try to edit a request using POST request.
    Note: Only Option field can be edited

    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    pass
