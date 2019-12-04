"""Test Service Details page functionality."""
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import providers
from cfme.services.myservice import MyService
from cfme.services.myservice.ssui import DetailsMyServiceView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils import ssh
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.conf import credentials
from cfme.utils.log import logger
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


@pytest.mark.long_running
@pytest.mark.parametrize('context', [ViaSSUI])
@pytest.mark.parametrize('order_service', [{'console_test': True}], indirect=True)
def test_vm_console(request, appliance, setup_provider, context, configure_websocket,
        configure_console_vnc, order_service, take_screenshot,
        console_template, provider):
    """Test Myservice VM Console in SSUI.

    Metadata:
        test_flag: ssui

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
    """
    if (provider.one_of(VMwareProvider) and provider.version >= 6.5 or
            'html5_console' in provider.data.get('excluded_test_flags', [])):
        pytest.skip('VNC consoles are unsupported on VMware ESXi 6.5 and later')

    catalog_item = order_service
    service_name = catalog_item.name
    console_vm_username = credentials[provider.data.templates.console_template
                            .creds].username
    console_vm_password = credentials[provider.data.templates.console_template
                            .creds].password
    with appliance.context.use(context):
        myservice = MyService(appliance, service_name)
        vm_obj = myservice.launch_vm_console(catalog_item)
        vm_console = vm_obj.vm_console
        if provider.one_of(OpenStackProvider):
            public_net = provider.data['public_network']
            vm_obj.mgmt.assign_floating_ip(public_net)
        request.addfinalizer(vm_console.close_console_window)
        request.addfinalizer(appliance.server.logout)
        ssh_who_command = ("who --count" if not provider.one_of(OpenStackProvider)
            else "who -aH")
        with ssh.SSHClient(hostname=vm_obj.ip_address, username=console_vm_username,
                password=console_vm_password) as vm_ssh_client:
            try:
                assert vm_console.wait_for_connect(180), ("VM Console did not reach 'connected'"
                    " state")
                user_count_before_login = vm_ssh_client.run_command(ssh_who_command,
                    ensure_user=True)
                logger.info("Output of '{}' is {} before login"
                    .format(ssh_who_command, user_count_before_login))
                assert vm_console.wait_for_text(text_to_find="login:", timeout=200), ("VM Console"
                    " didn't prompt for Login")
                # Enter Username:
                vm_console.send_keys("{}".format(console_vm_username))
                assert vm_console.wait_for_text(text_to_find="Password", timeout=200), ("VM Console"
                " didn't prompt for Password")
                # Enter Password:
                vm_console.send_keys("{}".format(console_vm_password))
                logger.info("Wait to get the '$' prompt")
                if not provider.one_of(OpenStackProvider):
                    vm_console.wait_for_text(text_to_find=provider.data.templates.
                        console_template.prompt_text, timeout=200)

                def _validate_login():
                    # the following try/except is required to handle the exception thrown by SSH
                    # while connecting to VMware VM.It throws "[Error 104]Connection reset by Peer".
                    try:
                        user_count_after_login = vm_ssh_client.run_command(ssh_who_command,
                            ensure_user=True)
                        logger.info("Output of '{}' is {} after login"
                            .format(ssh_who_command, user_count_after_login))
                        return user_count_before_login < user_count_after_login
                    except Exception as e:
                        logger.info("Exception: {}".format(e))
                        logger.info("Trying again to perform 'who --count' over ssh.")
                        return False

                # Number of users before login would be 0 and after login would be 180
                # If below assertion would fail user_count_after_login is also 0,
                # denoting login failed
                wait_for(func=_validate_login, timeout=300, delay=5)
                # create file on system
                vm_console.send_keys("touch blather")
                wait_for(func=vm_ssh_client.run_command, func_args=["ls blather"],
                    func_kwargs={'ensure_user': True},
                    fail_condition=lambda result: result.rc != 0, delay=1, num_sec=10)
                # if file was created in previous steps it will be removed here
                # we will get instance of SSHResult
                command_result = vm_ssh_client.run_command("rm blather", ensure_user=True)
                assert command_result

            except Exception:
                # Take a screenshot if an exception occurs
                vm_console.switch_to_console()
                take_screenshot("ConsoleScreenshot")
                vm_console.switch_to_appliance()
                raise


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


@pytest.mark.meta(coverage=[1677744])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_no_error_while_fetching_the_service():
    """

    Bugzilla:
        1677744

    Polarion:
        assignee: nansari
        startsin: 5.11
        casecomponent: SelfServiceUI
        initialEstimate: 1/6h
        testSteps:
            1. Provision service in regular UI with user that isn't admin
            2. Delete user, then go view the service in the SUI and see if it blows up.
        expectedResults:
            1.
            2. In SUI click on provisioned service
    """
    pass


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


@pytest.mark.meta(coverage=[1695804])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_service_dialog_check_on_ssui():
    """
    Bugzilla:
        1695804
    Polarion:
        assignee: nansari
        startsin: 5.11
        casecomponent: SelfServiceUI
        initialEstimate: 1/6h
        testSteps:
            1. Import datastore and import dialog
            2. Add catalog item with above dialog
            3. Navigate to order page of service
            4. Order the service
            5. Login into SSUI Portal
            6. Go MyService and click on provisioned service
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. Automation code shouldn't load when opening a service
    """
    pass


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
