# -*- coding: utf-8 -*-
"""Test Service Details page functionality."""
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.services.myservice import MyService
from cfme.services.myservice.ssui import DetailsMyServiceView
from cfme.utils import ssh
from cfme.utils.appliance import ViaSSUI
from cfme.utils.blockers import BZ, GH
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate", blockers=[GH('ManageIQ/integration_tests:7297')]),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[InfraProvider, CloudProvider],
                                                 required_fields=['provisioning'])])
]


@pytest.mark.rhv1
@pytest.mark.meta(blockers=[BZ(1544535, forced_streams=['5.9']),
    GH('ManageIQ/integration_tests:7297')])
@pytest.mark.parametrize('context', [ViaSSUI])
def test_myservice_crud(appliance, setup_provider, context, order_service):
    """Test Myservice crud in SSUI."""
    catalog_item = order_service
    with appliance.context.use(context):
        my_service = MyService(appliance, catalog_item.name)
        my_service.set_ownership("Administrator", "EvmGroup-approver")
        my_service.update({'description': '{}_edited'.format(catalog_item.name)})
        if appliance.version > "5.8":
            my_service.edit_tags("Cost Center", "Cost Center 001")
        my_service.delete()


@pytest.mark.meta(blockers=[BZ(1544535, forced_streams=['5.9']),
    GH('ManageIQ/integration_tests:7297')])
@pytest.mark.parametrize('context', [ViaSSUI])
def test_retire_service_ssui(appliance, setup_provider,
                        context, order_service, request):
    """Test retire service."""
    catalog_item = order_service
    with appliance.context.use(context):
        my_service = MyService(appliance, catalog_item.name)
        my_service.retire()

        @request.addfinalizer
        def _finalize():
            my_service.delete()


@pytest.mark.rhv3
@pytest.mark.parametrize('context', [ViaSSUI])
def test_service_start(appliance, setup_provider, context,
                       order_service, provider, request):
    """Test service stop"""
    catalog_item = order_service
    with appliance.context.use(context):
        my_service = MyService(appliance, catalog_item.name)
        if provider.one_of(InfraProvider):
            # For Infra providers vm is provisioned.Hence Stop option is shown
            my_service.service_power(power='Stop')
            view = my_service.create_view(DetailsMyServiceView)
            view.notification.assert_message(
                "{} was {}.".format(catalog_item.name, 'stopped'))
        else:
            my_service.service_power(power='Start')
            view = my_service.create_view(DetailsMyServiceView)
            view.notification.assert_message(
                "{} was {}.".format(catalog_item.name, 'started'))

        @request.addfinalizer
        def _finalize():
            my_service.delete()


@pytest.mark.meta(blockers=[BZ(1544535, forced_streams=['5.9'])])
@pytest.mark.parametrize('context', [ViaSSUI])
@pytest.mark.parametrize('order_service', [['console_test']], indirect=True)
@pytest.mark.uncollectif(lambda provider:
    provider.one_of(VMwareProvider) and provider.version >= 6.5 or
    'html5_console' in provider.data.get('excluded_test_flags', []),
    'VNC consoles are unsupported on VMware ESXi 6.5 and later')
def test_vm_console(request, appliance, setup_provider, context, configure_websocket,
        configure_console_vnc, order_service, take_screenshot,
        console_template, provider):
    """Test Myservice VM Console in SSUI."""
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
            provider.mgmt.assign_floating_ip(vm_obj.name, public_net)
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

            except Exception as e:
                # Take a screenshot if an exception occurs
                vm_console.switch_to_console()
                take_screenshot("ConsoleScreenshot")
                vm_console.switch_to_appliance()
                raise e
