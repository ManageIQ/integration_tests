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


@test_requirements.rest
@pytest.mark.manual()
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1727948])
def test_create_picture_with_role():
    """
    Polarion:
    assignee: pvala
    caseimportance: high
    casecomponent: Rest
    initialEstimate: 1/4h
    testSteps:
        1. Navigate to add role page and select every role individually.
        2. Create a group and user with the new role.
        3. Send a POST request to create a picture and check the response.
        4. Navigate to edit role page, uncheck `Everything` and recheck.
        5. Send a POST request to create a picture and check the response.
    expectedResults:
        1.
        2.
        3. Picture must be created without any error.
            Check for `Use of Action create is forbidden` in response.
        4.
        5. Picture must be created.

    Bugzilla:
        1727948
    """
    pass


@test_requirements.rest
@pytest.mark.manual()
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1700378])
def test_notification_url_parallel_requests():
    """
    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        testSteps:
            1. Stop evmserverd.
            2. Run `bin rails/server`
            3. Monitor production.log
            4. Run ruby script which will execute multiple api requests parallely.
                ```
                2.times do
                    Thread.new do
                        `curl -L https://admin:smartvm@localhost/api/vms`
                    end
                    Thread.new do
                        `curl -L https://admin:smartvm@localhost/api/notifications?
                        expand=resources&attributes=details&sort_by=id&sort_order=desc&limit=100`
                    end
                end
                ```
            5. Validate logs.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Check if all the requests were processed and completed

    Bugzilla:
        1700378
    """
    pass


@test_requirements.rest
@pytest.mark.manual()
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1684681])
def test_filtering_vm_with_multiple_ips():
    """
    Polarion:
        assignee: pvala
        caseimportance: high
        casecomponent: Rest
        initialEstimate: 1/4h
        setup:
            1. Add a provider.
        testSteps:
            1. Select a VM with multiple IP addresses and note one ipaddress.
            2. Send a GET request with the noted ipaddress.
                GET /api/vms?expand=resources&attributes=ipaddresses&filter[]=ipaddresses=':ipaddr'
        expectedResults:
            1.
            2. Selected VM must be present in the resources sent by response.

    Bugzilla:
        1684681
    """
    pass
