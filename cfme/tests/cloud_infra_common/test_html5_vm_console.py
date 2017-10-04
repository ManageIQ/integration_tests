# -*- coding: utf-8 -*-
"""Test for HTML5 Remote Consoles of VMware/RHEV/RHOSP Providers."""
import pytest
import imghdr
import time
import re

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common.provider import CloudInfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.common.vm import VM
from cfme.utils import testgen, version, ssh
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.conf import credentials
from cfme.utils.providers import ProviderFilter
from wait_for import wait_for

pytestmark = pytest.mark.usefixtures('setup_provider')

pytest_generate_tests = testgen.generate(
    gen_func=testgen.providers,
    filters=[ProviderFilter(classes=[CloudInfraProvider], required_flags=['html5_console'])],
    scope='module'
)


@pytest.fixture(scope="function")
def vm_obj(request, provider, setup_provider, console_template, vm_name):
    """
    Create a VM on the provider with the given template, and return the vm_obj.

    Also, it will remove VM from provider using nested function _delete_vm
    after the test is completed.

    """
    vm_obj = VM.factory(vm_name, provider, template_name=console_template.name)

    @request.addfinalizer
    def _delete_vm():
        try:
            vm_obj.delete_from_provider()
        except Exception:
            logger.warning("Failed to delete vm `{}`.".format(vm_obj.name))

    vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip="default")
    if provider.one_of(OpenStackProvider):
        # Assign FloatingIP to Openstack Instance from pool 'public'
        # so that we can SSH to it
        provider.mgmt.assign_floating_ip(vm_obj.name, 'public')
    return vm_obj


@pytest.fixture(scope="module")
def configure_vmware_console_for_test(appliance, provider):
    """Configure VMware Console to use VNC which is what is required for the HTML5 console."""
    if provider.one_of(VMwareProvider):
        appliance.server.settings.update_vmware_console({'console_type': 'VNC'})


@pytest.fixture(scope="session")
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


@pytest.mark.uncollectif(lambda: version.current_version() < '5.8', reason='Only valid for >= 5.8')
def test_html5_vm_console(appliance, provider, configure_websocket, vm_obj,
        configure_vmware_console_for_test, take_screenshot):
    """
    Test the HTML5 console support for a particular provider.

    The supported providers are:

        VMware
        Openstack
        RHV

    For a given provider, and a given VM, the console will be opened, and then:

        - The console's status will be checked.
        - A command that creates a file will be sent through the console.
        - Using ssh we will check that the command worked (i.e. that the file
          was created.
    """
    console_vm_username = credentials[provider.data.templates.get('console_template')
                            ['creds']].get('username')
    console_vm_password = credentials[provider.data.templates.get('console_template')
                            ['creds']].get('password')

    vm_obj.open_console(console='VM Console')
    assert vm_obj.vm_console, 'VMConsole object should be created'
    vm_console = vm_obj.vm_console
    try:
        # If the banner/connection-status element exists we can get
        # the connection status text and if the console is healthy, it should connect.
        assert vm_console.wait_for_connect(180), "VM Console did not reach 'connected' state"

        # Get the login screen image, and make sure it is a jpeg file:
        screen = vm_console.get_screen()
        assert imghdr.what('', screen) == 'jpeg'

        assert vm_console.wait_for_text(text_to_find="login:", timeout=200), ("VM Console"
            " didn't prompt for Login")

        # Enter Username:
        vm_console.send_keys(console_vm_username)

        assert vm_console.wait_for_text(text_to_find="Password", timeout=200), ("VM Console"
            " didn't prompt for Password")
        # Enter Password:
        vm_console.send_keys("{}\n".format(console_vm_password))

        time.sleep(5)  # wait for login to complete

        # This regex can find if there is a word 'login','password','incorrect' present in
        # text, irrespective of its case
        regex_for_login_password = re.compile(r'\blogin\b | \bpassword\b| \bincorrect\b',
         flags=re.I | re.X)

        def _validate_login():
            """
            Try to read what is on present on the last line in console.

            If it is word 'login', enter username, if 'password' enter password, in order
            to make the login successful
            """
            if vm_console.find_text_on_screen(text_to_find='login', current_line=True):
                vm_console.send_keys(console_vm_username)

            if vm_console.find_text_on_screen(text_to_find='Password', current_line=True):
                vm_console.send_keys("{}\n".format(console_vm_password))
            # if the login attempt failed for some reason (happens with RHOS-cirros),
            # last line of the console will contain one of the following words:
            # [login, password, incorrect]
            # if so, regex_for_login_password will find it and result will not be []
            # .split('\n')[-1] splits the console text on '\n' & picks last item of resulting list
            result = regex_for_login_password.findall(vm_console.get_screen_text().split('\n')[-1])
            return result == []

        # if _validate_login() returns True, it means we did not find any of words
        # [login, password, incorrect] on last line of console text, which implies login success
        wait_for(func=_validate_login, timeout=300, delay=5)

        logger.info("Wait to get the '$' prompt")
        if provider.one_of(VMwareProvider):
            vm_console.wait_for_text(text_to_find=provider.data.templates.get('console_template')
                            ['prompt_text'], timeout=200)
        else:
            time.sleep(15)

        # create file on system
        vm_console.send_keys("touch blather")
        if not (BZ.bugzilla.get_bug(1491387).is_opened):
            # Test pressing ctrl-alt-delete...we should be able to get a new login prompt:
            vm_console.send_ctrl_alt_delete()
            assert vm_console.wait_for_text(text_to_find="login:", timeout=200,
                to_disappear=True), ("Text 'login:' never disappeared, indicating failure"
                " of CTRL+ALT+DEL button functionality, please check if OS reboots on "
                "CTRL+ALT+DEL key combination and CTRL+ALT+DEL button on HTML5 Console is working.")
            assert vm_console.wait_for_text(text_to_find="login:", timeout=200), ("VM Console"
                " didn't prompt for Login")

        if not provider.one_of(OpenStackProvider):
            assert vm_console.send_fullscreen(), ("VM Console Toggle Full Screen button does"
            " not work")

        with ssh.SSHClient(hostname=vm_obj.ip_address, username=console_vm_username,
                password=console_vm_password) as ssh_client:
            # if file was created in previous steps it will be removed here
            # we will get instance of SSHResult
            # Sometimes Openstack drops characters from word 'blather' hence try to remove
            # file using partial file name. Known issue, being worked on.
            command_result = ssh_client.run_command("rm blather", ensure_user=True)
            assert command_result
    except:
        # Take a screenshot if an exception occurs
        vm_console.switch_to_console()
        take_screenshot("ConsoleScreenshot")
        vm_console.switch_to_appliance()
        raise
    finally:
        vm_console.close_console_window()
        # Logout is required because when running the Test back 2 back against RHV and VMware
        # Providers, following issue would arise:
        # If test for RHV is just finished, code would proceed to adding VMware Provider and once it
        # is added, then it will navigate to Infrastructure -> Virtual Machines Page, it will see
        # "Page Does not Exists" Error, because the browser will try to go to the
        # VM details page of RHV VM which is already deleted
        # at the End of test for RHV Provider Console and test would fail.
        # Logging out would get rid of this issue.
        appliance.server.logout()
