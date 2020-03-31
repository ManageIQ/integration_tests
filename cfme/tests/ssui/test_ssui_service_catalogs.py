import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import providers
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance.implementations.ssui import navigate_to
from cfme.utils.providers import ProviderFilter

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.provider(
        selector=ONE_PER_TYPE,
        gen_func=providers,
        filters=[ProviderFilter(
            classes=[InfraProvider, CloudProvider],
            required_fields=['provisioning'])]
    )
]


@pytest.mark.parametrize('context', [ViaSSUI])
def test_service_catalog_crud_ssui(appliance, setup_provider,
                                   context, order_service):
    """Tests Service Catalog in SSUI.

    Metadata:
        test_flag: ssui

    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        initialEstimate: 1/4h
        tags: ssui
    """

    catalog_item = order_service
    with appliance.context.use(context):
        dialog_values = {'service_name': fauxfactory.gen_alphanumeric(start="ssui_")}
        service = ServiceCatalogs(appliance, name=catalog_item.name,
                                  dialog_values=dialog_values)
        service.add_to_shopping_cart()
        service.order()


@pytest.mark.manual
@pytest.mark.tier(2)
def test_ssui_myservice_myrequests_and_service_catalog_filter_links():
    """ Check Filter Links of all pages
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: ssui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_ssui_test_all_language_translations():
    """
    desc
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        initialEstimate: 1/6h
        testtype: functional
        startsin: 5.10
        tags: ssui
    """
    pass


@pytest.mark.customer_scenario
@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1496233])
def test_ssui_disable_notification(request, appliance, user_self_service_role,
                                   generic_catalog_item):
    """
    Bugzilla:
        1496233

    Polarion:
        assignee: nansari
        startsin: 5.10
        casecomponent: SelfServiceUI
        initialEstimate: 1/6h
    """
    user, role = user_self_service_role

    product_features = [(['Everything', 'Service UI', 'Core', 'Notifications'], False)]
    role.update({'product_features': product_features})

    # login with user having self service role
    with user:
        with appliance.context.use(ViaSSUI):
            appliance.server.login(user)

            # order service from catalog item
            serv_cat = ServiceCatalogs(
                appliance,
                catalog=generic_catalog_item.catalog,
                name=generic_catalog_item.name,
            )

            view = navigate_to(serv_cat, 'Details')

            # Add Service to Shopping Cart
            view.add_to_shopping_cart.click()
            assert not view.notification.assert_message("Item added to shopping cart")

            # Clear Service from the Shopping Cart
            view = navigate_to(serv_cat, 'ShoppingCart')
            view.clear.click(handle_alert=True)
            assert view.alert.read() == "Shopping cart is empty."


@pytest.mark.manual
@pytest.mark.tier(2)
def test_in_ssui_portal_reconfigure_service_should_shows_available_provisioning_dialog():
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/2h
        startsin: 5.9
        tags: ssui
    Bugzilla:
        1633453
    """
    pass


@pytest.mark.tier(1)
def test_refresh_ssui_page(appliance, generic_service):
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.8
        tags: ssui
    """
    service, _ = generic_service

    with appliance.context.use(ViaSSUI):
        view = navigate_to(service, "Details")

        # After refresh it should be on the same page or shouldn't logout
        view.browser.refresh()
        assert view.is_displayed


@pytest.mark.manual
@pytest.mark.tier(3)
def test_able_to_access_openstack_instance_console_from_self_service_portal():
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        initialEstimate: 1/2h
        testtype: functional
        startsin: 5.9
        tags: ssui
    Bugzilla:
        1624573
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_notifications_should_appear_in_sui_after_enableing_embedded_ansible_role():
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/16h
        startsin: 5.9
        tags: ssui
    Bugzilla:
        1637512
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_sui_service_explorer_will_also_show_child_services():
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: ssui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_sui_ordering_service_catalog_the_dynamic_drop_down_dialogs_fields_should_auto_refreshed():
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: ssui
    Bugzilla:
        1568342
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_disabling_dashboard_under_service_ui_for_a_role_shall_disable_the_dashboard():
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: ssui
    Bugzilla:
        1589409
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_sui_order_and_request_should_be_sorted_by_time():
    """
    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: ssui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_sui_create_snapshot_when_no_provider_is_connected():
    """

    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: ssui
    Bugzilla:
        1440966
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_sui_monitor_ansible_playbook_std_output():
    """

    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: ssui
    Bugzilla:
        1437210
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_sui_snapshots_for_vm_create_edit_delete():
    """

    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: ssui
    """
    pass
