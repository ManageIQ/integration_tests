import fauxfactory
import pytest
import tempfile

from widgetastic.exceptions import UnexpectedAlertPresentException

from cfme.fixtures.v2v import _form_data
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name='second_provider'
    )
]


@pytest.fixture(scope="function")
def infra_map(appliance, v2v_providers):
    """Fixture to create infrastructure mapping"""
    form_data = _form_data(v2v_providers.vmware_provider, v2v_providers.rhv_provider)
    return appliance.collections.v2v_mappings.create(form_data)


def migration_plan(appliance, infra_map, csv=False):
    """Function to create migration plan and select csv import option"""
    plan_name = "map_{}".format(fauxfactory.gen_alpha(10))
    plan_obj = appliance.collections.v2v_plans
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
            if appliance.version >= '5.10.0.19':
                # Version check due to change in order of valid vms
                plan_view.vms.table[0][1].widget.click()
            else:
                plan_view.vms.table[2][1].widget.click()
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
def archived_vm(appliance, second_provider):
    """Fixture to create archived vm"""
    vm_obj = appliance.collections.infra_vms.instantiate(
        random_vm_name(context='v2v-auto'), second_provider)
    if not second_provider.mgmt.does_vm_exist(vm_obj.name):
        vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm_obj.mgmt.delete()
    vm_obj.wait_for_vm_state_change(desired_state='archived', timeout=900,
                                    from_details=False, from_any_provider=True)
    return vm_obj.name


def test_non_csv(appliance, infra_map):
    """Test non-csv file import"""
    error_msg = "Invalid file extension. Only .csv files are accepted."
    assert import_and_check(appliance, infra_map, error_msg, filetype='txt', alert=True)


def test_blank_csv(appliance, infra_map):
    """Test csv with blank file"""
    error_msg = "Error: Possibly a blank .CSV file"
    assert import_and_check(appliance, infra_map, error_msg)


def test_column_headers(appliance, infra_map):
    """Test csv with unsupported column header"""
    content = fauxfactory.gen_alpha(10)
    error_msg = "Error: Required column 'Name' does not exist in the .CSV file"
    assert import_and_check(appliance, infra_map, error_msg, content=content)


def test_inconsistent_columns(appliance, infra_map):
    """Test csv with extra inconsistent column value"""
    content = "Name\n{}, {}".format(fauxfactory.gen_alpha(10), fauxfactory.gen_alpha(10))
    error_msg = "Error: Number of columns is inconsistent on line 2"
    assert import_and_check(appliance, infra_map, error_msg, content=content)


@pytest.mark.meta(blockers=[BZ(1639239, forced_streams=["5.10"])])
def test_csv_empty_vm(appliance, infra_map):
    """Test csv with empty column value"""
    content = "Name\n\n"
    error_msg = "Empty name specified"
    assert import_and_check(appliance, infra_map, error_msg, content=content, table_hover=True)


@pytest.mark.meta(blockers=[BZ(1639239, forced_streams=["5.10"])])
def test_csv_invalid_vm(appliance, infra_map):
    """Test csv with invalid vm name"""
    content = "Name\n{}".format(fauxfactory.gen_alpha(10))
    error_msg = "VM does not exist"
    assert import_and_check(appliance, infra_map, error_msg, content=content, table_hover=True)


def test_csv_valid_vm(appliance, infra_map, valid_vm):
    """Test csv with valid vm name"""
    content = "Name\n{}".format(valid_vm)
    error_msg = "VM available for migration"
    assert import_and_check(appliance, infra_map, error_msg, content=content, table_hover=True)


def test_csv_duplicate_vm(appliance, infra_map, valid_vm):
    """Test csv with duplicate vm name"""
    content = "Name\n{}\n{}".format(valid_vm, valid_vm)
    error_msg = "Duplicate VM"
    assert import_and_check(appliance, infra_map, error_msg, content=content,
                            table_hover='duplicate')


@pytest.mark.meta(blockers=[BZ(1639239, forced_streams=["5.10"])])
def test_csv_archived_vm(appliance, infra_map, archived_vm):
    """Test csv with archived vm name"""
    content = "Name\n{}".format(archived_vm)
    error_msg = "VM is inactive"
    assert import_and_check(appliance, infra_map, error_msg, content=content, table_hover=True)
