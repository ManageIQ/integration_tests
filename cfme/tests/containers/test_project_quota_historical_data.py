import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.tier(0),
    test_requirements.containers,
    pytest.mark.manual('manualonly')
]


def test_cmqe_add_new_resource_quota():
    """
    Add new resource quota

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1h
        testSteps:
            1. On the Openshift provider, create different namespaces and
               assign them Resource Quotas. Assign different fractional
               values to the CPU quotas like  `1.152` or `0.087` or `87m`.
            2. Refresh the CFME appliance
            3. Check the containers_quota_items table in the database
            4. Navigate to the namespace in the CFME GUI.
            5. Refresh the CFME appliance
            6. Check the containers_quota_items table in the database
        expectedResults:
            1. Resource Quota assigned successfully.
            2. Appliance refreshed successfully.
            3. Database in `container_quota_items` table should contain
               both old and current values.            Newly added quotas
               should have `created_at` field set.
            4. Verify the GUI displays the correct data and the fractional
               values are formatted properly.
            5. Appliance refreshed successfully.
            6. Verify duplicate records were not added to the table
    """
    pass


def test_cmqe_modify_existing_resource_quota():
    """
    Modify Existing Quota

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1h
        testSteps:
            1. Modify the existing Resource Quota that was added;
            2. Refresh the CFME appliance
            3. Check the containers_quota_items table in the database
            4. Navigate to the namespace in the CFME GUI.
            5. Modify the existing Resource Quota again
            6. Refresh the CFME appliance
            7. Check the containers_quota_items table in the database
            8. Navigate to the namespace in the CFME GUI.
        expectedResults:
            1. Verify the update was successful
            2. Appliance refreshed successfully.
            3. Verify the modified values (eg. increased cpu) should appear
               as multiple rows — old value with `deleted_on` field set,
               and new value with approximately same `created_at`.
            4. Verify the GUI displays the correct data and the fractional
               values are formatted properly.
            5. Verify the update was successful
            6. Appliance refreshed successfully.
            7. Verify multiple values with both (created_at, deleted_on)
               set and only last one with deleted_on=null.
            8. Verify the GUI displays the correct data and the fractional
               values are formatted properly.
    """
    pass


def test_cmqe_delete_existing_resource_quota():
    """
    Delete existing Resource Quota

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1h
        testSteps:
            1. Delete the existing Resource Quota that was added;
            2. Refresh the CFME appliance
            3. Check the containers_quota_items table in the database
            4. Navigate to the namespace in the CFME GUI.
        expectedResults:
            1. Verify the Resource Quota was deleted successfully
            2. Appliance refreshed successfully.
            3. Verify the deleted Resource Quotas should still exist, with
               `deleted_on` field set.
            4. Verify the GUI displays no data referencing Resource Quota.
    """
    pass
