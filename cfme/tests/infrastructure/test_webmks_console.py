# -*- coding: utf-8 -*-
"""Test for WebMKS Remote Consoles of VMware Providers."""
import imghdr
import pytest
import socket

from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.utils import version, ssh
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from wait_for import wait_for
from markers.env_markers.provider import providers


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[InfraProvider],
                                                 required_flags=['webmks_console'])],
                         scope='module'),
]


@pytest.yield_fixture(scope="function")
def vm_obj(request, provider, setup_provider, console_template, vm_name):
    """VM creation/deletion fixture.

    Create a VM on the provider with the given template, and return the vm_obj.
    Also, remove VM from provider using nested function _delete_vm
    after the test is completed.
    """
    vm_obj = VM.factory(vm_name, provider, template_name=console_template.name)
    vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip="default")
    yield vm_obj
    try:
        vm_obj.delete_from_provider()
    except Exception:
        logger.warning("Failed to delete vm `{}`.".format(vm_obj.name))


@pytest.fixture(scope="module")
def configure_vmware_console_for_test(appliance):
    """Configure VMware Console to use VNC which is what is required for the HTML5 console."""
    appliance.server.settings.update_vmware_console({'console_type': 'VMware WebMKS'})


@pytest.yield_fixture
def ssh_client(vm_obj, console_template):
    """Provide vm_ssh_client for ssh operations in the test."""
    console_vm_username = credentials.get(console_template.creds).username
    console_vm_password = credentials.get(console_template.creds).password
    with ssh.SSHClient(hostname=vm_obj.ip_address, username=console_vm_username,
            password=console_vm_password) as vm_ssh_client:
        yield vm_ssh_client


@pytest.fixture(scope="module")
def configure_websocket(appliance):
    """
    Enable websocket role if it is disabled.

    Currently the fixture cfme/fixtures/base.py,
    disables the websocket role to avoid intrusive popups.
    """
    server_settings = appliance.server.settings
    roles = server_settings.server_roles_db
    if 'websocket' in roles and not roles['websocket']:
        logger.info('Enabling the websocket role to allow console connections')
        server_settings.enable_server_roles('websocket')
        yield
    logger.info('Disabling the websocket role to avoid intrusive popups')
    server_settings.disable_server_roles('websocket')


def test_webmks_vm_console(request, appliance, provider, vm_obj, configure_websocket,
        configure_vmware_console_for_test, take_screenshot, ssh_client):
    """Test the VMware WebMKS console support for a particular provider.

    The supported providers are:
        VMware vSphere6 and vSphere6.5

    For a given provider, and a given VM, the console will be opened, and then:

        - The console's status will be checked.
        - A command that creates a file will be sent through the console.
        - Using ssh we will check that the command worked (i.e. that the file
          was created.)
    """
    console_vm_username = credentials[provider.data.templates.get('console_template')
                            ['creds']].get('username')
    console_vm_password = credentials[provider.data.templates.get('console_template')
                            ['creds']].get('password')

    vm_obj.open_console(console='VM Console', invokes_alert=True)
    assert vm_obj.vm_console, 'VMConsole object should be created'
    vm_console = vm_obj.vm_console

    request.addfinalizer(vm_console.close_console_window)
    request.addfinalizer(appliance.server.logout)
    try:
        if appliance.version >= '5.9':
            # Since connection status element is only available in latest 5.9
            assert vm_console.wait_for_connect(180), "VM Console did not reach 'connected' state"
        # Get the login screen image, and make sure it is a jpeg file:
        screen = vm_console.get_screen(180)
        assert imghdr.what('', screen) == 'jpeg'

        assert vm_console.wait_for_text(text_to_find="login:", timeout=200),\
            "VM Console didn't prompt for Login"

        def _get_user_count_before_login():
            try:
                result = ssh_client.run_command("who --count", ensure_user=True)
                return result.rc == 0, result
            except socket.error as e:
                if e.errno == socket.errno.ECONNRESET:
                    logger.exception("Socket Error Occured: [104] Connection Reset by peer.")
                logger.info("Trying again to perform 'who --count' over ssh.")
                return False

        result_before_login, _ = wait_for(func=_get_user_count_before_login,
                                timeout=300, delay=5)
        result_before_login = result_before_login[1]
        logger.info("Output of who --count is {} before login".format(result_before_login))
        # Enter Username:
        vm_console.send_keys(console_vm_username)

        assert vm_console.wait_for_text(text_to_find="Password", timeout=200),\
            "VM Console didn't prompt for Password"
        # Enter Password:
        vm_console.send_keys("{}\n".format(console_vm_password))

        logger.info("Wait to get the '$' prompt")

        vm_console.wait_for_text(text_to_find=provider.data.templates.get('console_template')
            ['prompt_text'], timeout=200)

        def _validate_login():
            # the following try/except is required to handle the exception thrown by SSH
            # while connecting to VMware VM.It throws "[Error 104]Connection reset by Peer".
            try:
                result_after_login = ssh_client.run_command("who --count",
                                            ensure_user=True)
                logger.info("Output of 'who --count' is {} after login"
                .format(result_after_login))
                return result_before_login < result_after_login
            except socket.error as e:
                if e.errno == socket.errno.ECONNRESET:
                    logger.exception("Socket Error Occured: [104] Connection Reset by peer.")
                logger.info("Trying again to perform 'who --count' over ssh.")
                return False

        # Number of users before login would be 0 and after login would be 180
        # If below assertion would fail result_after_login is also 0,
        # denoting login failed
        wait_for(func=_validate_login, timeout=300, delay=5)

        # create file on system
        vm_console.send_keys("touch blather\n")
        vm_console.send_keys("\n\n")

        if appliance.version >= '5.9':
            # Since these buttons are only available in latest 5.9
            vm_console.send_ctrl_alt_delete()
            assert vm_console.wait_for_text(text_to_find="login:", timeout=200,
                to_disappear=True), ("Text 'login:' never disappeared, indicating failure"
                " of CTRL+ALT+DEL button functionality, please check if OS reboots on "
                "CTRL+ALT+DEL key combination and CTRL+ALT+DEL button on HTML5 Console is working.")
            assert vm_console.wait_for_text(text_to_find="login:", timeout=200), ("VM Console"
                " didn't prompt for Login")
            assert vm_console.send_fullscreen(), ("VM Console Toggle Full Screen button does"
                " not work")

        wait_for(func=ssh_client.run_command, func_args=["ls blather"],
            func_kwargs={'ensure_user': True}, handle_exception=True,
            fail_condition=lambda result: result.rc != 0, delay=1, num_sec=60)
        # if file was created in previous steps it will be removed here
        # we will get instance of SSHResult
        # Sometimes Openstack drops characters from word 'blather' hence try to remove
        # file using partial file name. Known issue, being worked on.
        command_result = ssh_client.run_command("rm blather", ensure_user=True)
        assert command_result

    except Exception as e:
        # Take a screenshot if an exception occurs
        vm_console.switch_to_console()
        take_screenshot("ConsoleScreenshot")
        vm_console.switch_to_appliance()
        raise e
