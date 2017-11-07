# -*- coding: utf-8 -*-
"""Test Service Details page functionality."""
import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.services.myservice import MyService
from cfme import test_requirements
from cfme.utils import testgen, ssh
from cfme.utils.appliance import ViaSSUI
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.version import current_version
from wait_for import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream", "5.9")
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.fixture(scope="module")
def configure_websocket(appliance):
    """Enable websocket role if it is disabled.

    Currently the fixture cfme/fixtures/base.py:27,
    disables the websocket role to avoid intrusive popups.
    """
    appliance.server.settings.enable_server_roles('websocket')
    logger.info('Enabling the websocket role to allow console connections')
    yield
    appliance.server.settings.disable_server_roles('websocket')
    logger.info('Disabling the websocket role to avoid intrusive popups')


@pytest.mark.parametrize('context', [ViaSSUI])
def test_myservice_crud(appliance, setup_provider, context, order_catalog_item_in_ops_ui):
    """Test Myservice crud in SSUI."""
    service_name = order_catalog_item_in_ops_ui.name
    with appliance.context.use(context):
        appliance.server.login()
        my_service = MyService(appliance, service_name)
        my_service.set_ownership("Administrator", "EvmGroup-approver")
        my_service.update({'description': '{}_edited'.format(service_name)})
        # No tag management in 5.7
        if appliance.version > "5.8":
            my_service.edit_tags("Cost Center", "Cost Center 001")
        my_service.delete()


@pytest.mark.uncollectif(lambda: current_version() < '5.8' or current_version() >= '5.9')
@pytest.mark.parametrize('context', [ViaSSUI])
@pytest.mark.parametrize('order_catalog_item_in_ops_ui', [['console_test']], indirect=True)
def test_vm_console(request, appliance, setup_provider, context, configure_websocket,
        order_catalog_item_in_ops_ui, take_screenshot, console_template):
    """Test Myservice VM Console in SSUI."""
    catalog_item = order_catalog_item_in_ops_ui
    service_name = catalog_item.name
    console_vm_username = credentials[catalog_item.provider.data.templates.console_template
                            .creds].username
    console_vm_password = credentials[catalog_item.provider.data.templates.console_template
                            .creds].password
    with appliance.context.use(context):
        appliance.server.login()
        myservice = MyService(appliance, service_name)
        vm_obj = myservice.launch_vm_console(catalog_item)
        vm_console = vm_obj.vm_console
        request.addfinalizer(vm_console.close_console_window)
        request.addfinalizer(appliance.server.logout)
        with ssh.SSHClient(hostname=vm_obj.ip_address, username=console_vm_username,
                password=console_vm_password) as vm_ssh_client:
            try:
                assert vm_console.wait_for_connect(180), ("VM Console did not reach 'connected'"
                    " state")
                user_count_before_login = vm_ssh_client.run_command("who --count", ensure_user=True)
                logger.info("Output of who --count is {} before login"
                    .format(user_count_before_login))
                assert vm_console.wait_for_text(text_to_find="login:", timeout=200), ("VM Console"
                    " didn't prompt for Login")
                # Enter Username:
                vm_console.send_keys("{}".format(console_vm_username))
                assert vm_console.wait_for_text(text_to_find="Password", timeout=200), ("VM Console"
                " didn't prompt for Password")
                # Enter Password:
                vm_console.send_keys("{}".format(console_vm_password))
                logger.info("Wait to get the '$' prompt")
                vm_console.wait_for_text(text_to_find=catalog_item.provider.data.templates.
                    console_template.prompt_text, timeout=200)

                def _validate_login():
                    # the following try/except is required to handle the exception thrown by SSH
                    # while connecting to VMware VM.It throws "[Error 104]Connection reset by Peer".
                    try:
                        user_count_after_login = vm_ssh_client.run_command("who --count",
                                                    ensure_user=True)
                        logger.info("Output of 'who --count' is {} after login"
                        .format(user_count_after_login))
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
