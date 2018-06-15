"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import pytest
import fauxfactory

from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.ignore_stream('5.8', '5.9')]


@pytest.fixture(scope="module")
def infra_map():
    # TODO: Remove this hardcoding by kk's infra_mapping code
    return "infra_map1"


@pytest.fixture(scope="module")
def vm_list():
    # TODO: Remove this code by dynamically creating vm objects
    return [vm1, vm2, vm3]


@pytest.mark.tier(0)
def test_compute_migration_modal(appliance):
    """Test takes an appliance and tries to navigate to migration page and open mapping wizard.

    This is a dummy test just to check navigation.
    # TODO : Replace this test with actual test.
    """
    infra_mapping_collection = appliance.collections.v2v_mappings
    view = navigate_to(infra_mapping_collection, 'All')
    assert view.is_displayed
    view = navigate_to(infra_mapping_collection, 'Add')
    assert view.is_displayed


@pytest.mark.parametrize('migration_flag', [True, False], ids=['start_migration', 'save_migration'])
@pytest.mark.parametrize('method', ['via_csv', 'via_discovery'])
def test_migration_plan_modal(appliance, infra_map, vm_list, method, migration_flag):
    if method == 'csv':
        csv_import = True
    else:
        csv_import = False
    coll = appliance.collections.migration_plan
    coll.create(name="plan_{}".format(fauxfactory.gen_alphanumeric()),
                description="desc_{}".format(fauxfactory.gen_alphanumeric()),
                infra_map=infra_map.name,
                vm_names=vm_list,
                csv_import=csv_import,
                start_migration=migration_flag)
