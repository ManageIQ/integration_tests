# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.meta(server_roles="+automate",
                     blockers=[BZ(1633540, forced_streams=['5.10'],
                        unblock=lambda provider: not provider.one_of(RHEVMProvider))]),
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider', 'catalog_item', 'uses_infra_providers'),
    test_requirements.dialog,
    pytest.mark.long_running,
    pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE,
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module")
]


@pytest.fixture(scope="function")
def tagcontrol_dialog(appliance):
    service_dialog = appliance.collections.service_dialogs
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = {
        'element_information': {
            'ele_label': "Service Level",
            'ele_name': "service_level",
            'ele_desc': "service_level_desc",
            'choose_type': "Tag Control",
        },
        'options': {
            'field_category': "Service Level",
            'field_required': True
        }
    }
    sd = service_dialog.create(label=dialog, description="my dialog")
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    box.elements.create(element_data=[element_data])
    yield sd


@pytest.fixture(scope="function")
def catalog(appliance):
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = appliance.collections.catalogs.create(name=catalog, description="my catalog")
    yield cat


@pytest.fixture(scope="function")
def catalog_item(appliance, provider, provisioning, tagcontrol_dialog, catalog):
    template, host, datastore, iso_file, vlan = list(map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'vlan')))

    provisioning_data = {
        'catalog': {'catalog_name': {'name': template, 'provider': provider.name},
                    'vm_name': random_vm_name('service')},
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore}},
        'network': {'vlan': partial_match(vlan)},
    }

    if provider.type == 'rhevm':
        provisioning_data['catalog']['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provisioning_data['catalog']['provision_type'] = 'VMware'
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalog_items.create(
        provider.catalog_item_type,
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=tagcontrol_dialog,
        prov_data=provisioning_data)
    return catalog_item


@pytest.mark.rhv2
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_tagdialog_catalog_item(appliance, provider, catalog_item, request):
    """Tests tag dialog catalog item
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).cleanup_on_provider()
    )
    dialog_values = {'service_level': "Gold"}
    service_catalogs = ServiceCatalogs(appliance, catalog=catalog_item.catalog,
                                       name=catalog_item.name,
                                       dialog_values=dialog_values)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Request failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg


@pytest.mark.manual
@pytest.mark.tier(2)
def test_dialogs_should_only_run_once():
    """ Dialogs should only run once
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        startsin: 5.9
        initialEstimate: 1/4h
        tags: service
    Bugzilla:
        1595776
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_triggered_refresh_shouldnt_occurs_for_dialog_after_changing_type_to_static():
    """ Triggered Refresh shouldn't Occurs for Dialog After Changing Type to Static
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1614436
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_timepicker_should_show_date_when_chosen_once():
    """ Timepicker should show date when chosen once
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.7
        tags: service
    Bugzilla:
        1638079
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_default_dialog_entries_should_localized_when_ordering_catalog_item_in_french():
    """ Default dialog entries should localized when ordering catalog item in French
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/16h
        startsin: 5.7
        tags: service
    Bugzilla:
        1592573
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_in_dynamic_dropdown_list_the_default_value_should_not_contain_all_the_value_of_the_list():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.10
        tags: service
    Bugzilla:
        1568440
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_saving_service_dialog_with_multi_select_drop_down_populated_by_expression_method():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1559030
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_cui_should_check_dialog_field_associations():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/6h
        startsin: 5.10
        tags: service
    Bugzilla:
        1559382
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_generic_object_should_be_visible_in_service_view():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        testtype: functional
        startsin: 5.8
        tags: service
    Bugzilla:
        1515945
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_reconfigure_service_for_dialogs_with_timeout_values():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.7
    Bugzilla:
        1442920
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_timepicker_should_pass_correct_timing_on_service_order():
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
def test_should_be_able_to_see_requests_if_our_users_are_in_groups_with_managed_tags():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1596738
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_user_should_be_able_to_change_the_order_of_values_of_the_drop_down_list():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/16h
        casecomponent: Services
        testtype: functional
        startsin: 5.10
        tags: service
    Bugzilla:
        1594301
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_search_field_at_the_top_of_a_dynamic_drop_down_dialog_element_should_display():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1553347
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_default_selection_of_dropdown_list_is_should_display_properly():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/6h
        startsin: 5.9
        tags: service
    Bugzilla:
        1579405
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_service_dialog_saving_elements_when_switching_elements():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: service
    Bugzilla:
        1454428
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_entries_shouldnt_be_mislabeled_for_dropdown_element_in_dialog_editor():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        testtype: functional
        startsin: 5.10
        tags: service
    Bugzilla:
        1597802
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_automate_methods_from_dynamic_dialog_should_run_as_per_designed():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/16h
        startsin: 5.9
        tags: service
    Bugzilla:
        1571000
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_reconfigure_existing_duplicate_orders():
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
@pytest.mark.tier(1)
def test_should_be_able_to_access_services_requests_as_user():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1576129
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_dialog_dropdown_ui_values_in_the_dropdown_should_be_visible_in_edit_mode():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/16h
        startsin: 5.9
        tags: service
    Bugzilla:
        1557508
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.parametrize('element_type', ['dropdown', 'text_box', 'checkbox', 'text_area',
                                          'radiobutton', 'date_picker', 'timepicker', 'tagcontrol'])
def test_dialog_elements_should_display_default_value(element_type):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/8h
        startsin: 5.10
        caseimportance: high
        testSteps:
            1. Create a dialog. Set default value
            2. Use the dialog in a catalog.
            3. Order catalog.
        expectedResults:
            1.
            2.
            3. Default values should be shown
    Bugzilla:
        1385898
    """
    pass
