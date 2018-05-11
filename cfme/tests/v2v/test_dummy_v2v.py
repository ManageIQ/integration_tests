import fauxfactory

from cfme.utils.appliance.implementations.ui import navigate_to


def test_dummy(appliance):
    """Test takes an appliance and tries to navigate and fill the form for Infra Map and Migration Plan.

    This is a dummy test just to check navigation.
    """
    migration_plan_collection = appliance.collections.migration_plan
    infrastructure_mapping_collection = appliance.collections.infrastructure_mapping

    add_infrastucture_mapping_view = navigate_to(infrastructure_mapping_collection, 'Add')
    add_infrastucture_mapping_view.name.fill("infra_map_" + fauxfactory.gen_alphanumeric())
    add_infrastucture_mapping_view.description.fill(fauxfactory.gen_string("alphanumeric",
     length=50))
    add_infrastucture_mapping_view.next_btn.click()
    add_infrastucture_mapping_view.back_btn.click()
    add_infrastucture_mapping_view.cancel_btn.click()

    add_migration_plan_view = navigate_to(migration_plan_collection, 'Add')
    add_migration_plan_view.name.fill("infra_map_" + fauxfactory.gen_alphanumeric())
    add_migration_plan_view.description.fill(fauxfactory.gen_string("alphanumeric",
     length=50))
    add_migration_plan_view.next_btn.click()
    add_migration_plan_view.back_btn.click()
    add_migration_plan_view.cancel_btn.click()
