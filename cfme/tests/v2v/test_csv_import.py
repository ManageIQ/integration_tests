import tempfile

import fauxfactory
import pytest
from widgetastic.exceptions import NoSuchElementException
from widgetastic.exceptions import UnexpectedAlertPresentException

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.v2v_fixtures import infra_mapping_default_data
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.v2v,
    pytest.mark.customer_scenario,
    pytest.mark.provider(
        classes=[RHEVMProvider, OpenStackProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup"),
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


def migration_plan(appliance, infra_map, csv=True):
    """Function to create migration plan and select csv import option"""
    if csv:
        import_btn = "Import a CSV file with a list of VMs to be migrated"
    else:
        import_btn = "Choose from a list of VMs discovered in the selected infrastructure mapping"
    plan_obj = appliance.collections.v2v_migration_plans
    view = navigate_to(plan_obj, 'Add')
    view.general.fill({
        "infra_map": infra_map.name,
        "name": fauxfactory.gen_alpha(10),
        "description": fauxfactory.gen_alpha(10),
        "choose_vm": import_btn
    })
    return view


def check_vm_status(appliance, infra_map, filetype='csv', content=False,
                    table_hover=False, alert=False, security_group=False):
    """Function to import csv, select vm and return hover error from migration plan table"""
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
        if table_hover == 'duplicate':
            plan_view.vms.table[0][1].widget.click()  # widget stands for tooltip widget
        else:
            # click on the checkbox to select VM (column 0)
            plan_view.vms.table[0][1].widget.click()
        if not security_group:
            error_msg = plan_view.vms.popover_text.read()
    else:
        if alert:
            error_msg = plan_view.browser.get_alert().text
            try:
                plan_view.browser.handle_alert()
            except NoSuchElementException:
                pass
        else:
            error_msg = plan_view.vms.error_text.text
    if security_group:
        plan_view.next_btn.click()
        plan_view.instance_properties.table.wait_displayed()
        table_data = plan_view.instance_properties.table.read()[0]
        error_msg = {
            "security_group": str(table_data["OpenStack Security Group"]),
            "flavor": str(table_data["OpenStack Flavor"])}
    plan_view.cancel_btn.click()
    return error_msg


@pytest.fixture(scope="function")
def valid_vm(appliance, infra_map):
    """Fixture to get valid vm name from discovery"""
    plan_view = migration_plan(appliance, infra_map, csv=False)
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
        assignee: sshveta
        caseposneg: negative
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    error_text = "Invalid file extension. Only .csv files are accepted."
    hover_error = check_vm_status(appliance, infra_map, error_text, filetype='txt', alert=True)
    assert error_text == hover_error


def test_blank_csv(appliance, infra_map):
    """Test csv with blank file
    Polarion:
        assignee: sshveta
        caseposneg: negative
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    error_msg = "Error: Possibly a blank .CSV file"
    hover_error = check_vm_status(appliance, infra_map, error_msg)
    assert error_msg == hover_error


def test_column_headers(appliance, infra_map):
    """Test csv with unsupported column header
    Polarion:
        assignee: sshveta
        caseposneg: positive
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    content = fauxfactory.gen_alpha(10)
    error_msg = "Error: Required column 'Name' does not exist in the .CSV file"
    hover_error = check_vm_status(appliance, infra_map, error_msg, content=content)
    assert error_msg == hover_error


def test_inconsistent_columns(appliance, infra_map):
    """Test csv with extra inconsistent column value
    Polarion:
        assignee: sshveta
        caseposneg: negative
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    content = "Name\n{}, {}".format(fauxfactory.gen_alpha(10), fauxfactory.gen_alpha(10))
    error_msg = "Error: Number of columns is inconsistent on line 2"
    hover_error = check_vm_status(appliance, infra_map, error_msg, content=content)
    assert error_msg == hover_error


def test_csv_empty_vm(appliance, infra_map):
    """Test csv with empty column value
    Polarion:
        assignee: sshveta
        caseposneg: positive
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    content = "Name\n\n"
    error_msg = "Empty name specified"
    hover_error = check_vm_status(
        appliance, infra_map, error_msg, content=content, table_hover=True)
    assert error_msg == hover_error


def test_csv_invalid_vm(appliance, infra_map):
    """Test csv with invalid vm name
    Polarion:
        assignee: sshveta
        caseposneg: negative
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    content = "Name\n{}".format(fauxfactory.gen_alpha(10))
    error_msg = "VM does not exist"
    hover_error = check_vm_status(
        appliance, infra_map, error_msg, content=content, table_hover=True)
    assert error_msg == hover_error


def test_csv_valid_vm(appliance, infra_map, valid_vm):
    """Test csv with valid vm name
    Polarion:
        assignee: sshveta
        caseposneg: positive
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    content = "Name\n{}".format(valid_vm)
    error_msg = "VM available for migration"
    hover_error = check_vm_status(
        appliance, infra_map, error_msg, content=content, table_hover=True)
    assert error_msg == hover_error


def test_csv_duplicate_vm(appliance, infra_map, valid_vm):
    """Test csv with duplicate vm name
    Polarion:
        assignee: sshveta
        caseposneg: positive
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    content = "Name\n{}\n{}".format(valid_vm, valid_vm)
    error_msg = "Duplicate VM"
    hover_error = check_vm_status(
        appliance, infra_map, error_msg, content=content, table_hover='duplicate')
    assert error_msg == hover_error


def test_csv_archived_vm(appliance, infra_map, archived_vm):
    """Test csv with archived vm name
    Polarion:
        assignee: sshveta
        caseposneg: positive
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/8h
    """
    content = "Name\n{}".format(archived_vm)
    error_msg = "VM is inactive"
    hover_error = check_vm_status(
        appliance, infra_map, error_msg, content=content, table_hover=True)
    assert error_msg == hover_error


@pytest.mark.provider(
    classes=[OpenStackProvider],
    selector=ONE_PER_VERSION,
    required_flags=["v2v"],
    scope="module",
)
@pytest.mark.provider(
    classes=[VMwareProvider],
    selector=ONE_PER_TYPE,
    fixture_name="source_provider",
    required_flags=["v2v"],
    scope="module",
)
def test_csv_security_group_flavor(appliance, soft_assert, infra_map, valid_vm, provider):
    """Test csv with secondary openstack security group and flavor
    Polarion:
        assignee: mnadeem
        caseposneg: positive
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1/4h
    """
    try:
        security_group = provider.data.security_groups.admin[1]
        flavor = provider.data.flavors[1]
    except (AttributeError, KeyError):
        pytest.skip("No provider data found.")
    content = f"Name,Security Group,Flavor\n{valid_vm},{security_group},{flavor}\n"

    expected_attributes = check_vm_status(appliance, infra_map, content=content,
                                          table_hover=True, security_group=True)

    soft_assert(expected_attributes["security_group"] == security_group)
    # In some case * appended in flavor name in GUI as a warning which can be safely ignore.
    assert expected_attributes["flavor"] in (flavor, f"{flavor} *")
