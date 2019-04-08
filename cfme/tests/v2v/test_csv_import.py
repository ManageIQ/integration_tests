import tempfile

import fauxfactory
import pytest
from widgetastic.exceptions import UnexpectedAlertPresentException

from cfme.fixtures.v2v_fixtures import infra_mapping_default_data, get_vm
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider], selector=ONE_PER_VERSION, required_flags=["v2v"], scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    # pytest.mark.usefixtures("v2v_provider_setup")
]


@pytest.fixture(scope="function")
def infra_map(appliance, mapping_data_vm_obj_mini):
    """Fixture to create infrastructure mapping"""
    # mapping_data = infra_mapping_default_data(source_provider, provider)
    mapping_data = mapping_data_vm_obj_mini.infra_mapping_data
    return appliance.collections.v2v_infra_mappings.create(**mapping_data)


def migration_plan(appliance, infra_map, csv=False):
    """Function to create migration plan and select csv import option"""
    plan_name = "map_{}".format(fauxfactory.gen_alpha(10))
    plan_obj = appliance.collections.v2v_migration_plans
    view = navigate_to(plan_obj, 'Add')
    view.general.fill({
        'infra_map': infra_map.name,
        'name': plan_name,
        'description': fauxfactory.gen_alpha(20)
    })
    if not csv:
        view.general.select_vm.select("Import a CSV file with a list of VMs to be migrated")
        view.next_btn.click()
    return view


def import_and_check(appliance, infra_map, error_text, filetype='csv', content=False,
                     table_hover=False, alert=False):
    plan_view = migration_plan(appliance, infra_map)
    temp_file = tempfile.NamedTemporaryFile(suffix='.{}'.format(filetype))
    if content:
        with open(temp_file.name, 'w') as f:
            f.write(content)
    try:
        plan_view.vms.hidden_field.fill(temp_file.name)
    except UnexpectedAlertPresentException:
        pass
    if table_hover:
        wait_for(lambda: plan_view.vms.is_displayed,
                 timeout=60, message='Wait for VMs view', delay=5)
        if table_hover is 'duplicate':
            if appliance.version >= '5.10':
                # Version check due to change in order of valid vms
                plan_view.vms.table[0][1].widget.click()  # widget stands for tooltip widget
            else:
                plan_view.vms.table[2][1].widget.click()  # widget stands for tooltip widget
        else:
            plan_view.vms.table[0][1].widget.click()
        error_msg = plan_view.vms.popover_text.read()
    else:
        if alert:
            error_msg = plan_view.browser.get_alert().text
            plan_view.browser.handle_alert()
        else:
            error_msg = plan_view.vms.error_text.text
    plan_view.cancel_btn.click()
    return bool(error_msg == error_text)


@pytest.fixture(scope="function")
def valid_vm(appliance, infra_map):
    """Fixture to get valid vm name from discovery"""
    plan_view = migration_plan(appliance, infra_map, csv=True)
    plan_view.next_btn.click()
    wait_for(lambda: plan_view.vms.is_displayed,
             timeout=60, delay=5, message='Wait for VMs view')
    vm_name = [row.vm_name.text for row in plan_view.vms.table.rows()][0]
    plan_view.cancel_btn.click()
    return vm_name


@pytest.fixture(scope="function")
def archived_vm(appliance, source_provider):
    """Fixture to create archived vm"""
    vm_obj = appliance.collections.infra_vms.instantiate(
        random_vm_name(context='v2v-auto'), source_provider)
    if not source_provider.mgmt.does_vm_exist(vm_obj.name):
        vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm_obj.mgmt.delete()
    vm_obj.wait_for_vm_state_change(desired_state='archived', timeout=900,
                                    from_details=False, from_any_provider=True)
    return vm_obj.name


def test_non_csv(appliance, mapping_data_vm_obj_mini):
    """Test non-csv file import

    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    error_text = "The selected file does not have the expected format."
    csv_params = {'filetype': 'txt',
                  'alert': True,
                  'error_text': error_text}
    with pytest.raises(AssertionError):
        migration_plan_collection = appliance.collections.v2v_migration_plans
        migration_plan_collection.create(
            name="plan_{}".format(fauxfactory.gen_alphanumeric()),
            description="desc_{}".format(fauxfactory.gen_alphanumeric()),
            infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get('name'),
            csv_import=True,
            csv_params=csv_params,
            vm_list=mapping_data_vm_obj_mini.vm_list
        )

    # assert import_and_check(appliance, infra_map, error_msg, filetype='txt', alert=True)



