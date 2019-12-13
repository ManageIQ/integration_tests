"""Test Service Details page functionality."""
from textwrap import dedent
from timeit import timeit

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import providers
from cfme.services.myservice import MyService
from cfme.services.myservice.ssui import DetailsMyServiceView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.appliance.implementations.ui import navigate_to as ui_nav
from cfme.utils.log_validator import LogValidator
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.ssui,
    pytest.mark.provider(
        selector=ONE_PER_TYPE,
        gen_func=providers,
        filters=[ProviderFilter(
            classes=[InfraProvider, CloudProvider],
            required_fields=['provisioning'])])
]


@pytest.mark.rhv1
@pytest.mark.long_running
@pytest.mark.parametrize('context', [ViaSSUI])
def test_myservice_crud(appliance, setup_provider, context, order_service):
    """Test Myservice crud in SSUI.

    Metadata:
        test_flag: ssui, services

    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        initialEstimate: 1/4h
        tags: ssui
    """
    catalog_item = order_service
    with appliance.context.use(context):
        my_service = MyService(appliance, catalog_item.name)
        my_service.set_ownership("Administrator", "EvmGroup-approver")
        my_service.update({'description': '{}_edited'.format(catalog_item.name)})
        my_service.edit_tags("Cost Center", "Cost Center 002")
        my_service.delete()


@pytest.mark.long_running
@pytest.mark.parametrize('context', [ViaSSUI])
def test_retire_service_ssui(appliance, setup_provider,
                        context, order_service, request):
    """Test retire service.

    Metadata:
        test_flag: ssui, services

    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        initialEstimate: 1/4h
        tags: ssui
    """
    catalog_item = order_service
    with appliance.context.use(context):
        my_service = MyService(appliance, catalog_item.name)
        my_service.retire()

        @request.addfinalizer
        def _finalize():
            my_service.delete()


@pytest.mark.rhv3
@pytest.mark.long_running
@pytest.mark.parametrize('context', [ViaSSUI])
def test_service_start(appliance, setup_provider, context,
                       order_service, provider, request):
    """Test service stop

    Metadata:
        test_flag: ssui, services

    Polarion:
        assignee: nansari
        casecomponent: SelfServiceUI
        initialEstimate: 1/4h
        tags: ssui
    """
    catalog_item = order_service
    with appliance.context.use(context):
        my_service = MyService(appliance, catalog_item.name)
        if provider.one_of(InfraProvider, EC2Provider, AzureProvider):
            # For Infra providers vm is provisioned.Hence Stop option is shown
            # For Azure, EC2 Providers Instance is provisioned.Hence Stop option is shown
            my_service.service_power(power='Stop')
            view = my_service.create_view(DetailsMyServiceView)
            wait_for(lambda: view.resource_power_status.power_status == 'Off',
                     timeout=1000,
                     fail_condition=None,
                     message='Wait for resources off',
                     delay=20)
        else:
            my_service.service_power(power='Start')
            view = my_service.create_view(DetailsMyServiceView)
            wait_for(lambda: view.resource_power_status.power_status == 'On',
                     timeout=1000,
                     fail_condition=None,
                     message='Wait for resources on',
                     delay=20)

        @request.addfinalizer
        def _finalize():
            my_service.delete()


@pytest.mark.manual
@test_requirements.ssui
@pytest.mark.tier(2)
@pytest.mark.parametrize('context', [ViaSSUI])
def test_suspend_vm_service_details(context):
    """
    Test suspending VM from SSUI service details page.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        setup:
            1. Have a service catalog item that provisions a VM
        testSteps:
            1. In SSUI, navigate to My Services -> <service name> to see service details
            2. In Resources section, choose 'Suspend' from dropdown
        expectedResults:
            1. Service details displayed
            2. VM is suspended; VM is NOT in Unknown Power State
    Bugzilla:
        1670373
    """
    pass


@pytest.mark.meta(automates=[1677744])
@pytest.mark.customer_scenario
@pytest.mark.tier(2)
def test_no_error_while_fetching_the_service(request, appliance, user_self_service_role,
                                             generic_catalog_item):
    """

    Bugzilla:
        1677744

    Polarion:
        assignee: nansari
        startsin: 5.10
        casecomponent: SelfServiceUI
        initialEstimate: 1/6h
        testSteps:
            1. Provision service in regular UI with user that isn't admin
            2. Delete user, then go view the service in the SUI and see if it blows up.
        expectedResults:
            1.
            2. In SUI click on provisioned service
    """
    user, _ = user_self_service_role

    # login with user having self service role
    with user:
        with appliance.context.use(ViaUI):
            appliance.server.login(user)

            # Order service from catalog item
            serv_cat = ServiceCatalogs(
                appliance,
                catalog=generic_catalog_item.catalog,
                name=generic_catalog_item.name,
            )
            provision_request = serv_cat.order()
            provision_request.wait_for_request()

            # Check service with user
            service = MyService(appliance, generic_catalog_item.dialog.label)
            assert service.exists

    @request.addfinalizer
    def _clear_service():
        if service.exists:
            service.delete()

    # Delete user
    # Note: before deleting user need to clean respected user requests
    provision_request.remove_request(method="rest")
    user.delete()
    assert not user.exists

    # Check service exist without user or not
    for context in [ViaUI, ViaSSUI]:
        with appliance.context.use(context):
            assert service.exists


@pytest.mark.meta(automates=[1628520])
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
@pytest.mark.parametrize('context', [ViaUI, ViaSSUI])
def test_retire_owned_service(request, appliance, context, user_self_service_role,
                              generic_catalog_item):
    """

    Bugzilla:
        1628520

    Polarion:
        assignee: nansari
        startsin: 5.11
        casecomponent: SelfServiceUI
        initialEstimate: 1/6h
        testSteps:
            1. Create a catalog item as User
            2. Provision service in regular UI with user
            3. Login to Service UI as User
            4. Try to retire the service
        expectedResults:
            1.
            2.
            3.
            4. Service should retire
    """
    user, _ = user_self_service_role

    # login with user having self service role
    with user:
        with appliance.context.use(context):
            appliance.server.login(user)

            # order service from catalog item
            serv_cat = ServiceCatalogs(
                appliance,
                catalog=generic_catalog_item.catalog,
                name=generic_catalog_item.name,
            )

            if context == ViaSSUI:
                serv_cat.add_to_shopping_cart()

            provision_request = serv_cat.order()
            provision_request.wait_for_request()
            service = MyService(appliance, generic_catalog_item.dialog.label)

            @request.addfinalizer
            def _clear_request_service():
                if provision_request.exists():
                    provision_request.remove_request(method="rest")
                if service.exists:
                    service.delete()

            assert service.exists

            # Retire service
            retire_request = service.retire()
            assert retire_request.exists()

            @request.addfinalizer
            def _clear_retire_request():
                if retire_request.exists():
                    retire_request.remove_request()

            wait_for(
                lambda: service.is_retired,
                delay=5, num_sec=120,
                fail_func=service.browser.refresh,
                message="waiting for service retire"
            )


@pytest.mark.customer_stories
@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1695804])
@pytest.mark.tier(2)
def test_service_dynamic_dialog_execution(appliance, request, custom_instance):
    """
    Bugzilla:
        1695804
    Polarion:
        assignee: nansari
        startsin: 5.11
        casecomponent: SelfServiceUI
        initialEstimate: 1/6h
        testSteps:
            1. Create custom instance and method
            2. Create dynamic dialog with above method
            3. Create Catalog and catalog item having dynamic dialog
            4. Order the service
            5. Access service with UI, SSUI, REST
        expectedResults:
            1.
            2.
            3.
            4.
            5. In all context, when opening a service automation code should not run
    """

    # Create custom instance with ruby method for dynamic dialog
    code = dedent(
        """
        sleep 20 # wait 20 seconds
        $evm.root['default_value'] = Time.now.to_s
        exit MIQ_OK
        """
    )
    instance = custom_instance(ruby_code=code)
    assert instance.exists
    matched_patterns = [f"System/Request/{instance.fields['meth1']['value']}", "MIQ_OK"]

    # Create dynamic dialog and entry point as ruby method
    service_dialog = appliance.collections.service_dialogs
    dialog = fauxfactory.gen_alphanumeric(12, start="dialog_")
    ele_name = fauxfactory.gen_alphanumeric(start="ele_")

    element_data = {
        "element_information": {
            "ele_label": fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            "ele_name": ele_name,
            "ele_desc": fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            "dynamic_chkbox": True,
            "choose_type": "Text Box",
        },
        "options": {"entry_point": instance.tree_path},
    }
    dialog = service_dialog.create(label=dialog, description="my dialog")
    tab = dialog.tabs.create(
        tab_label=fauxfactory.gen_alphanumeric(start="tab_"), tab_desc="my tab desc"
    )
    box = tab.boxes.create(
        box_label=fauxfactory.gen_alphanumeric(start="box_"), box_desc="my box desc"
    )
    box.elements.create(element_data=[element_data])
    request.addfinalizer(dialog.delete_if_exists)

    # Create catalog and catalog item with dialog
    catalog = appliance.collections.catalogs.create(
        name=fauxfactory.gen_alphanumeric(start="cat_"),
        description=fauxfactory.gen_alphanumeric(15, start="cat_desc_"),
    )
    assert catalog.exists
    request.addfinalizer(catalog.delete_if_exists)

    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
        description=fauxfactory.gen_alphanumeric(20, start="cat_item_desc_"),
        display_in=True,
        catalog=catalog,
        dialog=dialog,
    )
    assert catalog_item.exists
    request.addfinalizer(catalog_item.delete_if_exists)

    # Order catalog item; check for method execution in log
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)

    with LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=matched_patterns
    ).waiting(timeout=60):
        # The expected time to land on dialog page: 20+ sec (script has 20 sec sleep)
        provision_request = service_catalogs.order(wait_for_view=30)

    provision_request.wait_for_request()
    service = MyService(appliance, catalog_item.name)

    @request.addfinalizer
    def _clean_request_service():
        if provision_request.exists:
            provision_request.remove_request(method="rest")
        if service.exists:
            service.delete()

    # Check service access with UI and SSUI should not run automate method
    for context in [ViaUI, ViaSSUI]:
        with appliance.context.use(context):
            # lets stay on Service All page before click on service
            navigate_to = ui_nav if context is ViaUI else ssui_nav
            navigate_to(service, "All")

            with LogValidator(
                "/var/www/miq/vmdb/log/automation.log", failure_patterns=matched_patterns
            ).waiting(timeout=60):
                assert timeit(lambda: navigate_to(service, "Details"), number=1) < 20

    # The API call should not takes 20 seconds (sleep time). i.e it should not call automate method.
    with LogValidator(
        "/var/www/miq/vmdb/log/automation.log", failure_patterns=matched_patterns
    ).waiting(timeout=60):
        assert timeit(lambda: service.rest_api_entity, number=1) < 2


@pytest.mark.meta(automates=[1743734])
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_list_supported_languages_on_ssui(appliance, soft_assert):
    """
    Bugzilla:
        1743734

    Polarion:
        assignee: nansari
        startsin: 5.11
        caseimportance: medium
        casecomponent: SelfServiceUI
        initialEstimate: 1/16h
        testSteps:
            1. Log into SSUI, see what languages are available
        expectedResults:
            1. Service UI should list the Supported languages:
    """
    with appliance.context.use(ViaSSUI):
        view = ssui_nav(appliance.server, "LoggedIn")

    for lang in ["Browser Default", "English", "Español", "Français", "日本語"]:
        # Its Dropdown with language options
        assert soft_assert(lang in view.settings.items[1])
