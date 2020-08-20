import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import providers
from cfme.services.dashboard.ssui import DashboardView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance.implementations.ssui import navigate_to
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for

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


@pytest.mark.tier(2)
@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1589409])
def test_ssui_disable_dashboard(appliance, user_self_service_role):
    """
    Bugzilla:
        1589409
    Polarion:
        assignee: nansari
        startsin: 5.11
        casecomponent: SelfServiceUI
        initialEstimate: 1/16h
    """
    user, role = user_self_service_role

    product_features = [(['Everything', 'Service UI', 'Dashboard'], False)]
    role.update({'product_features': product_features})

    # login with user having self service role
    with user:
        with appliance.context.use(ViaSSUI):
            appliance.server.login(user)

            view = appliance.browser.create_view(DashboardView)
            # Dashboard should not be present
            assert not view.is_displayed


@pytest.mark.customer_scenario
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1437210])
def test_ssui_ansible_playbook_stdout(appliance, ansible_service_catalog, ansible_service_request,
                                      ansible_service):
    """ Test standard output of ansible playbook service
    Bugzilla:
        1437210
    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: SelfServiceUI
        setup:
            1. Create ansible playbook
        testSteps:
            1. Create ansible playbook service catalog item
            2. Create service catalog
            3. Order service
            4. Log in into SSUI
            5. Navigate to My Services->Service details
            6. check stdout of service
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. able to see standard output
    """
    ansible_service_catalog.order()
    ansible_service_request.wait_for_request()

    with appliance.context.use(ViaSSUI):
        view = navigate_to(ansible_service, "Details")
        assert view.standard_output.is_displayed
        wait_for(lambda: view.standard_output.text != "Loading...", timeout=30)
        assert "Hello World" in view.standard_output.text
