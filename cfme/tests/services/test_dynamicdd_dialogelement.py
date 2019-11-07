# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.services.service_catalogs import ServiceCatalogs

pytestmark = [
    pytest.mark.long_running,
    test_requirements.dialog,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles="+automate")
]

item_name = fauxfactory.gen_alphanumeric(15, start="cat_item_")

METHOD_TORSO = """
# Method for logging
def log(level, message)
  @method = 'Service Dialog Provider Select'
  $evm.log(level, "#{@method} - #{message}")
end

# Start Here
log(:info, " - Listing Root Object Attributes:") if @debug
$evm.root.attributes.sort.each { |k, v| $evm.log('info', "#{@method} - \t#{k}: #{v}") if @debug }
log(:info, "===========================================") if @debug

        dialog_field = $evm.object
        dialog_field['data_type'] = 'string'
        dialog_field['required']  = 'true'
        dialog_field['sort_by']   = 'value'
        dialog_field["values"] = [[1, "one"], [2, "two"], [10, "ten"], [50, "fifty"]]
"""


@pytest.fixture(scope="function")
def dialog(appliance, copy_instance, create_method):
    service_dialogs = appliance.collections.service_dialogs
    dialog = fauxfactory.gen_alphanumeric(12, start="dialog_")
    sd = service_dialogs.create(label=dialog, description="my dialog")
    tab = sd.tabs.create(tab_label=fauxfactory.gen_alphanumeric(start="tab_"),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label=fauxfactory.gen_alphanumeric(start="box_"),
        box_desc="my box desc")
    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(start="ele_"),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Dropdown"
        },
        'options': {
            'dynamic_chkbox': True
        }
    }
    box.elements.create(element_data=[element_data])
    yield sd


@pytest.fixture(scope="function")
def catalog(appliance):
    cat_name = fauxfactory.gen_alphanumeric(start="cat_")
    catalog = appliance.collections.catalogs.create(name=cat_name, description="my catalog")
    yield catalog


@pytest.fixture(scope="function")
def copy_domain(request, appliance):
    domain = DomainCollection(appliance).create(name="new_domain", enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    return domain


@pytest.fixture(scope="function")
def create_method(request, copy_domain):
    return copy_domain\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')\
        .methods.create(
            name='InspectMe',
            location='inline',
            script=METHOD_TORSO)


@pytest.fixture(scope="function")
def copy_instance(request, copy_domain, appliance):
    miq_domain = DomainCollection(appliance).instantiate(name='ManageIQ')
    instance = miq_domain\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')\
        .instances.instantiate(name='InspectMe')
    instance.copy_to(copy_domain)


@pytest.mark.tier(3)
def test_dynamicdropdown_dialog(appliance, dialog, catalog):
    """
    Bugzilla:
        1514584

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        tags: service
    """
    item_name = fauxfactory.gen_alphanumeric(15, start="cat_item_")
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC, name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog)
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()


@pytest.mark.manual
@pytest.mark.tier(3)
def test_submit_or_cancelation_btns_in_dd_dialogs_tied_to_a_service_button_should_be_visble():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1611527
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_drop_down_dialog_should_honor_the_order_of_values_as_they_are_inputted():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1593874
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_dynamic_dropdowns_should_show_value_only_once():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_dd_multiselect_default_element_is_shouldnt_be_blank_when_loaded_by_another_element():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1645555
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_expression_method_definitions_should_not_fail_with_script_error_in_a_dialog():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.10
        tags: service
    Bugzilla:
        1558926
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_dialog_text_box_triggers_fields_shouldnt_refresh_too_soon_often():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        testtype: functional
        startsin: 5.10
        tags: service
    Bugzilla:
        1614321
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_ssui_dd_values_are_not_loaded_in_dropdown_unless_refresh_button_is_pressed():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.8
        tags: service
    Bugzilla:
        1322594
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_in_dynamic_multi_select_dialog_elements_the_first_element_shouldnt_be_selected():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1322594
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_textbox_value_should_update_with_automate_method():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1613443
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_when_clicking_refresh_for_text_field_2_only_text_field_2_should_refreshed():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
        testSteps:
            1.  create a dialog with two text fields with no refresh relation between them
                showing their refresh buttons.
            2. associate each to a different method that just logs "Refreshing X"
            3. associating the dialog to a catalog item
            4. tail -f log/automation.log | grep "Refreshing"
            5. load the dialog
            6. click "refresh" for field 2
    Bugzilla:
        1559999
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_second_dialog_dynamic_element_should_be_able_to_read_the_previous_textbox_element():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        tags: service
        testSteps:
            1. import example automate domain
            2. import example service dialog
            3. create a generic catalog item with the dialog service dialog provided
    Bugzilla:
        1576107
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_automation_executed_on_field_refresh_are_called_twice_in_self_service_dialogs():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h

    Bugzilla:
        1576873
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_dynamic_drop_down_dialog_should_work_with_automate_expression_method():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1583694
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_drop_down_list_dialog_does_should_keep_default_value_for_integer_type_in_dialogs():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1554780
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_dynamic_dropdown_values_should_load_correctly():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
        testSteps:
            1. Import the dialog and domain attached
            2. Select Contract A . Contract B gets selected
            3. In Location no values are loaded
    Bugzilla:
        1581996
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_child_dialog_should_update_with_new_options_based_on_option_of_parent_dialog_upon_ref():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1580535
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_value_input_into_service_dialog_element():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/16h
        startsin: 5.5
    Bugzilla:
        1364407
    """
    pass
