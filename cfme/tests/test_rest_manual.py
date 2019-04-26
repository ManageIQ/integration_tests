# -*- coding: utf-8 -*-
"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_cloud_volume_types():
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/30h
        startsin: 5.10
        setup:
            1. Add a cloud provider to the appliance.
        testSteps:
            1. Send GET request: /api/cloud_volume_types/:id
        expectedResults:
            1. Successful 200 OK response.
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
@pytest.mark.parametrize("auth_type", ["token", "basic_auth"])
def test_populate_default_dialog_values(auth_type):
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/10h
        setup:
            1. Navigate to Configuration(menu) > Server > Advanced
                and set `run_automate_methods_on_service_api_submit` to `true`.
            2. Create a new domain, `domain_1`.
            3. Create a Method, let's say `method_1` (Method is attached in the Bugzilla 1639413z).
                This method sets value 2 for static element and 7 for dynamic element,
                both of which must be reflected in the response.
            4. Create an instance, let's say `instance_1`.
            5. Create a Dialog with one static element
                (name="static", value_type="Integer", read_only=True, required=True)
                with some default value, and one dynamic element
                (name="dynamic", value_type="Integer", read_only=True, required=True)
                with the endpoint pointing to `method_1` which returns default value.
            6. Create a Catalog, say `catalog_1`.
            7. Create a Generic Catalog item under the newly create Catalog, say `catalog_item_1`.
            8. Get the `service_catalog` id and `service_template` id.
        testSteps:
            1. Order the service with the given auth_type
                and check if the response contains default values that were initially set.
        expectedResults:
            1. Response must include default values that were initially set.

        Bugzilla:
            1635673
            1650252
            1639413
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_create_rhev_provider_with_metric():
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
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
        casecomponent: Rest
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
@pytest.mark.tier(3)
def test_add_ansible_tower_rest():
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/10h
        testSteps:
            1. Add Ansible Tower via REST
        expectedResults:
            1. Provider must be added and validated successfully.

    Bugzilla:
        1621888
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_delete_vm_disk_via_api():
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/10h
        setup:
            1. Add an infrastructure provider. Test this vcenter and rhv provider.
            2. Provision a VM.
            3. Add a disk to the VM.
        testSteps:
            1. Delete the disk via API.
        expectedResults:
            1. The disk must be deleted successfully.

    Bugzilla:
        1666593
        1620161
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
def test_add_vm_disk_via_api():
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/10h
        setup:
            1. Add an infrastructure provider. Test this vcenter and rhv provider.
            2. Provision a VM.
        testSteps:
            1. Add a disk to the VM.
        expectedResults:
            1. The disk must be added successfully.

    Bugzilla:
        1618517
    """
    pass


@pytest.mark.manual
@test_requirements.rest
@pytest.mark.tier(3)
@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_delete_automate_domain_via_api(method):
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/10h
        setup:
            1. Create an automate domain.
        testSteps:
            1. Delete the automate domain via REST
        expectedResults:
            1. Domain must be deleted successfully.
    """
    pass
