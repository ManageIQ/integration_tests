# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.workloads import VmsInstances
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for_decorator


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running,
    pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE,
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module"),
]


@pytest.mark.rhv1
@pytest.mark.tier(2)
def test_order_catalog_item(appliance, provider, catalog_item, request,
                            register_event):
    """Tests order catalog item
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).cleanup_on_provider()
    )

    register_event(target_type='Service', target_name=catalog_item.name,
                   event_type='service_provisioned')

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Provisioning failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg


@test_requirements.rest
@pytest.mark.rhv3
@pytest.mark.tier(2)
def test_order_catalog_item_via_rest(
        request, appliance, provider, catalog_item, catalog):
    """Same as :py:func:`test_order_catalog_item`, but using REST.
    Metadata:
        test_flag: provision, rest

    Polarion:
        assignee: pvala
        casecomponent: Services
        caseimportance: high
        initialEstimate: 1/3h
        tags: service
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(vm_name,
                                                            provider).cleanup_on_provider()
    )
    request.addfinalizer(catalog_item.delete)
    catalog = appliance.rest_api.collections.service_catalogs.find_by(name=catalog.name)
    assert len(catalog) == 1
    catalog, = catalog
    template = catalog.service_templates.find_by(name=catalog_item.name)
    assert len(template) == 1
    template, = template
    req = template.action.order()
    assert_response(appliance)

    @wait_for_decorator(timeout="15m", delay=5)
    def request_finished():
        req.reload()
        logger.info("Request status: {}, Request state: {}, Request message: {}".format(
            req.status, req.request_state, req.message))
        return req.status.lower() == "ok" and req.request_state.lower() == "finished"


@pytest.mark.rhv3
@pytest.mark.tier(2)
def test_order_catalog_bundle(appliance, provider, catalog_item, request):
    """Tests ordering a catalog bundle
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """

    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).cleanup_on_provider()
    )
    bundle_name = fauxfactory.gen_alphanumeric()
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog,
        dialog=catalog_item.dialog, catalog_items=[catalog_item.name])
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_bundle.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(bundle_name))
    request_description = bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Provisioning failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg


@pytest.mark.skip('Catalog items are converted to collections. Refactoring is required')
@pytest.mark.rhv3
# Note here this needs to be reduced, doesn't need to test against all providers
@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(3)
def test_no_template_catalog_item(provider, provisioning, dialog, catalog, appliance):
    """Tests no template catalog item
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/8h
        tags: service
    """
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalogs.instantiate(
        # TODO pass catalog class for instantiation
        item_type=provider.catalog_name, name=item_name,
        description="my catalog", display_in=True, catalog=catalog, dialog=dialog)
    with pytest.raises(Exception, match="'Catalog/Name' is required"):
        catalog_item.create()


@pytest.mark.rhv3
@pytest.mark.tier(3)
def test_request_with_orphaned_template(appliance, provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provider.delete()
    provider.wait_for_delete()
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.status.text == 'Error'


@pytest.mark.rhv3
@test_requirements.filtering
@pytest.mark.tier(3)
def test_advanced_search_registry_element(request, appliance):
    """
        Go to Services -> Workloads
        Advanced Search -> Registry element
        Element types select bar shouldn't disappear.

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    view = navigate_to(VmsInstances(appliance=appliance), 'All')
    view.search.open_advanced_search()
    request.addfinalizer(view.search.close_advanced_search)
    view.search.advanced_search_form.search_exp_editor.registry_form_view.fill({'type': "Registry"})
    assert view.search.advanced_search_form.search_exp_editor.registry_form_view.type.is_displayed


@pytest.mark.manual
@pytest.mark.tier(2)
def test_email_should_be_sent_when_service_approval_is_set_to_manual():
    """ Email should be sent when service approval is set to manual
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: service
    Bugzilla:
        1380197
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_role_configured_with_the_option_only_user_or_group_owned_should_allow_to_access_to_se():
    """ Role configured with the option "only user or group owned
        should allow to access to service catalogs and items
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1554775
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_notification_banner_vm_provisioning_notification_and_service_request_should_be_in_syn():
    """ Notification Banner - VM Provisioning Notification and Service Request should be in  Sync
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.7
        tags: service
    Bugzilla:
        1389312
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_database_wildcard_should_work_and_be_included_in_the_query():
    """ Database wildcard should work and be included in the query
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.10
        tags: service
    Bugzilla:
        1581853
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_user_should_be_able_to_see_requests_irrespective_of_tags_assigned():
    """ User should be able to see requests irrespective of tags assigned
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        testtype: functional
        startsin: 5.9
        tags: service
    Bugzilla:
        1641012
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_changing_action_order_in_catalog_bundle_should_not_removes_resource():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        testtype: functional
        startsin: 5.8
        tags: service
    Bugzilla:
        1615853
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_notification_banner_service_event_should_be_shown_in_notification_bell():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        testtype: functional
        startsin: 5.9
        tags: service
        testSteps:
            1. OPS UI  and SSUI service requests should create an event in notification bell
            2. Also check , Clear All and "MArk as read" in notification bell
            3. Number of events shown in notification bell
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_reconfigure_service_fields_empty_after_deploying_service():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: service
    Bugzilla:
        1580987
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_order_service_after_deleting_provider():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: service
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_custom_image_on_item_bundle_crud():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: service
        testSteps:
            1. Create a catalog item
            2. Upload custom image
            3. remove custom image
            4. Create a catalog  bundle
            5. Upload a custom image
            6. Change custom image
        expectedResults:
            1.
            2. No error seen
            3.
            4.
            5. No error seen
    Bugzilla:
        1487056
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_catalog_item_changing_the_provider_template_after_filling_all_tabs():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.5
        tags: service
    Bugzilla:
        1240443
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_retire_ansible_service_bundle():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.5
        tags: service
    Bugzilla:
        1363897
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_remove_catalog_items_from_catalog_bundle_resource_list():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
    Bugzilla:
        1639557
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_request_filter_on_request_page():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1498237
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_check_all_availability_zones_for_amazon_provider():
    """ Check if all availability zones can be selected while creating catalog item.
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: service
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_service_retirement_requests_shall_be_run_by_the_user():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: service
        testSteps:
            1. Create a request from non-admin user. Request shall be run by user
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_edit_catalog_item_after_remove_resource_pool():
    """ Create catalog item with a resource pool , Remove resource pool from
        the provider and then edit catalog item.
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: service
        testSteps:
            1. Create a catalog item
            2. Select cluster and resource pool and Save
            3. Remove resource pool from provider
            4. Edit catalog
        expectedResults:
            1.
            2.
            3.
            4. Validation message should be shown
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_create_generic_instance():
    """
    Polarion:
        assignee: nansari
        casecomponent: Automate
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1577395
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_generic_object_details_displayed_from_a_service_do_not_include_associations():
    """
    Polarion:
        assignee: nansari
        casecomponent: Automate
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    Bugzilla:
        1576828
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.service
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.parametrize('catalog_location', ['global', 'remote'])
@pytest.mark.parametrize('item_type', ['AMAZON', 'ANSIBLE', 'TOWER', 'AZURE', 'GENERIC',
                                       'OPENSTACK', 'ORCHESTRATION', 'RHV', 'SCVMM', 'VMWARE'])
def test_service_provision_retire_from_global_region(item_type, catalog_location, context):
    """
    Polarion:
        assignee: izapolsk
        caseimportance: medium
        casecomponent: Services
        initialEstimate: 1/3h
    """
    pass
