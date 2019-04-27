import tempfile

import fauxfactory
import pytest
from widgetastic.exceptions import UnexpectedAlertPresentException

from cfme.fixtures.v2v_fixtures import infra_mapping_default_data
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
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
    pytest.mark.usefixtures("v2v_provider_setup")
]


@pytest.fixture(scope="function")
def infra_map(appliance, source_provider, provider):
    """Fixture to create infrastructure mapping"""
    infra_mapping_data = infra_mapping_default_data(
        source_provider, provider)
    infra_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping = infra_mapping_collection.create(**infra_mapping_data)
    yield mapping
    infra_mapping_collection.delete(mapping)


def migration_plan(appliance, infra_map):
    """Function to create migration plan and select csv import option"""
    import_btn = "Import a CSV file with a list of VMs to be migrated"
    plan_obj = appliance.collections.v2v_migration_plans
    view = navigate_to(plan_obj, 'Add')
    view.general.fill({
        "infra_map": infra_map.name,
        "name": fauxfactory.gen_alpha(10),
        "description": fauxfactory.gen_alpha(10),
        "choose_vm": import_btn
    })

    view.next_btn.click()
    return view


def import_and_check(appliance, infra_map, error_text=None,
                     filetype='csv', content=False, table_hover=False, alert=False):
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
        # click on the checkbox to select VM (column 0)
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


def test_non_csv(appliance, infra_map):
    """Test non-csv file import

    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    error_text = "Invalid file extension. Only .csv files are accepted."
    assert import_and_check(appliance, infra_map, error_text, filetype='txt', alert=True)


def test_blank_csv(appliance, infra_map):
    """Test csv with blank file
    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    error_msg = "Error: Possibly a blank .CSV file"
    assert import_and_check(appliance, infra_map, error_msg)


def test_column_headers(appliance, infra_map):
    """Test csv with unsupported column header
    Polarion:
        assignee: ytale
        initialEstimate: 1/4h
        casecomponent: V2V
    """
    content = fauxfactory.gen_alpha(10)
    error_msg = "Error: Required column 'Name' does not exist in the .CSV file"
    assert import_and_check(appliance, infra_map, error_msg, content=content)


def test_inconsistent_columns(appliance, infra_map):
    """Test csv with extra inconsistent column value
    Polarion:
        assignee: ytale
        initialEstimate: 1/4h
        casecomponent: V2V
    """
    content = "Name\n{}, {}".format(fauxfactory.gen_alpha(10), fauxfactory.gen_alpha(10))
    error_msg = "Error: Number of columns is inconsistent on line 2"
    assert import_and_check(appliance, infra_map, error_msg, content=content)


@pytest.mark.meta(blockers=[BZ(1699343, forced_streams=["5.10"])])
def test_csv_empty_vm(appliance, infra_map):
    """Test csv with empty column value
    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    content = "Name\n\n"
    error_msg = "Empty name specified"
    assert import_and_check(appliance, infra_map, error_msg,
                            content=content, table_hover=True)


@pytest.mark.meta(blockers=[BZ(1699343, forced_streams=["5.10"])])
def test_csv_invalid_vm(appliance, infra_map):
    """Test csv with invalid vm name
    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    content = "Name\n{}".format(fauxfactory.gen_alpha(10))
    error_msg = "VM does not exist"
    assert import_and_check(appliance, infra_map, error_msg,
                            content=content, table_hover=True)


@pytest.mark.meta(blockers=[BZ(1699343, forced_streams=["5.10"])])
def test_csv_valid_vm(appliance, infra_map, valid_vm):
    """Test csv with valid vm name
    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    content = "Name\n{}".format(valid_vm)
    error_msg = "VM available for migration"
    assert import_and_check(appliance, infra_map, error_msg,
                            content=content, table_hover=True)


@pytest.mark.meta(blockers=[BZ(1699343, forced_streams=["5.10"])])
def test_csv_duplicate_vm(appliance, infra_map, valid_vm):
    """Test csv with duplicate vm name
    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    content = "Name\n{}\n{}".format(valid_vm, valid_vm)
    error_msg = "Duplicate VM"
    assert import_and_check(appliance, infra_map, error_msg, content=content,
                            table_hover='duplicate')


@pytest.mark.meta(blockers=[BZ(1699343, forced_streams=["5.10"])])
def test_csv_archived_vm(appliance, infra_map, archived_vm):
    """Test csv with archived vm name
    Polarion:
        assignee: ytale
        casecomponent: V2V
        customerscenario: true
        initialEstimate: 1/8h
        subcomponent: RHV
        upstream: yes
    """
    content = "Name\n{}".format(archived_vm)
    error_msg = "VM is inactive"
    assert import_and_check(appliance, infra_map, error_msg,
                            content=content, table_hover=True)
