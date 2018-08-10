import pytest

"""
Description:
RFE to keep history of quota changes in our DB
https://bugzilla.redhat.com/show_bug.cgi?id=1504560

Success Criteria:
You need to refresh; change quotas — change values (main use case), add new ones,
delete some; then refresh again.We're talking of ResourceQuota objects only.
https://kubernetes.io/docs/concepts/policy/resource-quotas/
1. UI should work as before, show current quotas, hide deleted quotas.
2. Database in `container_quota_items` table should contain both old and current values.
    Rows in this table are not deleted, nor updated in-place.
    - Newly added quotas should have `created_at` field set.
    - Deleted quotas should still exist, with `deleten_on` field set.
    - Modified values (eg. increased cpu) should appear as multiple rows — old value with
    `deleten_on` field set, and new value with approximately same `created_at`.
    - If you modify & re-refresh more than once, you should see multiple values
    with both (created_at, deleted_on) set and only last one with deleted_on=null.

A lot of the effort was around precision issues with fractional values.
most quota values are integers, only cpu quotas take fractional values ("millicores")
so test some cpu quota(s) with values like `1.152` or `0.087` or `87m`.
- test that when you do NOT modify such a quota and refresh again, it's not duplicated.
- test the UI shows the fractional value nicely (not say as "0.08700000000000001")

A handy command to inspect the DB table in rails console:

    puts ContainerQuotaItem.order(:updated_at).map(&:attributes).tableize

or in SQL (psql -U root vmdb_production to connect to the DB)

    select * from container_quota_items;

"""


@pytest.mark.manual
def add_new_kubernetes_resource_quota():
    """
    - On the Openshift provider, create different namespaces and assign them Resource Quotas.
    Assign different fractional values to the CPU quotas like `1.152` or `0.087` or `87m`.
    - Verify Resource Quota assigned successfully.
    - Refresh the CFME appliance
    - Verify appliance refreshed successfully.
    - Check the containers_quota_items table in the database
    - Database in `container_quota_items` table should contain both old and current values.
    Newly added quotas should have `created_at` field set.
    - Navigate to the namespace in the CFME GUI.
    - Verify the GUI displays the correct data and the fractional values are formatted properly.
    - Refresh the CFME appliance
    - Verify appliance refreshed successfully.
    - Check the containers_quota_items table in the database
    - Verify duplicate records were not added to the table
    """
    pass


@pytest.mark.manual
def modify_existing_kubernetes_resource_quota():
    """
    - Modify the existing Resource Quota that was added in add_new_kubernetes_resource_quota()
    - Verify the update was successful
    - Refresh the CFME appliance
    - Verify appliance refreshed successfully.
    - Check the containers_quota_items table in the database
    - Verify the modified values (eg. increased cpu) should appear as multiple rows — old value
    with `deleted_on` field set, and new value with approximately same `created_at`.
    - Navigate to the namespace in the CFME GUI.
    - Verify the GUI displays the correct data and the fractional values are formatted properly.
    - Modify the existing Resource Quota again
    - Verify the update was successful
    - Refresh the CFME appliance
    - Verify appliance refreshed successfully.
    - Check the containers_quota_items table in the database
    - Verify multiple values with both (created_at, deleted_on) set
    and only last one with deleted_on=null.
    - Navigate to the namespace in the CFME GUI.
    - Verify the GUI displays the correct data and the fractional values are formatted properly.
    """
    pass


@pytest.mark.manual
def delete_existing_kubernetes_resource_quota():
    """
    - Delete the existing Resource Quota that was modified in
    modify_existing_kubernetes_resource_quota()
    -  Verify the Resource Quota was deleted successfully
    - Refresh the CFME appliance
    - Verify appliance refreshed successfully.
    - Check the containers_quota_items table in the database
    - Verify the deleted Resource Quotas should still exist, with `deleted_on` field set.
    - Navigate to the namespace in the CFME GUI.
    - Verify the GUI displays no data referencing Resource Quota.
    """
    pass
