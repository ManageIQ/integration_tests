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
def test_automation_request_task():
    """
    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        testSteps:
            1. Create an automation request.
            2. Edit the automation request task:
                POST /api/automation_requests/:id/request_tasks/:request_task_id
                {
                "action" : "edit",
                "resource" : {
                    "options" : {
                    "request_param_a" : "value_a",
                    "request_param_b" : "value_b"
                    }
                }
        expectedResults:
            1.
            2. Task must be edited successfully.

    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_edit_provider_request_task():
    """
    Polarion:
        assignee: pvala
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Rest
        testSteps:
            1. Create a provision request.
            2. Edit the provision request task:
                POST /api/provision_requests/:id/request_tasks/:request_task_id
                {
                "action" : "edit",
                "resource" : {
                    "options" : {
                    "request_param_a" : "value_a",
                    "request_param_b" : "value_b"
                    }
                }
        expectedResults:
            1.
            2. Task must be edited successfully.
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_provider_specific_vm():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Add multiple provider and query vms related to a specific provider.
                GET /api/providers/:provider_id/vms
        expectedResults:
            1. Should receive all VMs related to the provider.
    """
    pass


@pytest.mark.manual
@test_requirements.rest
def test_edit_request_task():
    """
        Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        testSteps:
            1. Create a service request.
            2. Edit the service request task:
                POST /api/service_requests/:id/request_tasks/:request_task_id
                {
                "action" : "edit",
                "resource" : {
                    "options" : {
                    "request_param_a" : "value_a",
                    "request_param_b" : "value_b"
                    }
                }
        expectedResults:
            1.
            2. Task must be edited successfully.

    """
    pass
