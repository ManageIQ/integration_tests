# -*- coding: utf-8 -*-
"""Test for WebMKS Remote Consoles of VMware Providers."""
import imghdr
import pytest
import re

from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.utils import testgen, version, ssh
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from wait_for import wait_for

pytestmark = pytest.mark.usefixtures('setup_provider')

pytest_generate_tests = testgen.generate(
    gen_func=testgen.providers,
    filters=[ProviderFilter(classes=[InfraProvider], required_flags=['webmks_console'])],
    scope='module'
)


@pytest.yield_fixture(scope="function")
def vm_obj(request, provider, setup_provider, console_template, vm_name):
    """VM creation/deletion fixture.

    Create a VM on the provider with the given template, and return the vm_obj.
    Also, remove VM from provider using nested function _delete_vm
    after the test is completed.
    """
    vm_obj = VM.factory(vm_name, provider, template_name=console_template)
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


@pytest.mark.uncollectif(lambda: version.current_version() < '5.8', reason='Only valid for >= 5.8')
def test_webmks_vm_console(request, appliance, provider, vm_obj,
        configure_vmware_console_for_test):
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

    # Get the login screen image, and make sure it is a jpeg file:
    screen = vm_console.get_screen(180)
    assert imghdr.what('', screen) == 'jpeg'

    with ssh.SSHClient(hostname=vm_obj.ip_address, username=console_vm_username,
            password=console_vm_password) as vm_ssh_client:
        assert vm_console.wait_for_text(text_to_find="login:", timeout=200),\
            "VM Console didn't prompt for Login"

        result_before_login = vm_ssh_client.run_command("who --count", ensure_user=True)
        # Enter Username:
        vm_console.send_keys(console_vm_username)

        assert vm_console.wait_for_text(text_to_find="Password", timeout=200),\
            "VM Console didn't prompt for Password"
        # Enter Password:
        vm_console.send_keys("{}\n".format(console_vm_password))

        result_after_login = vm_ssh_client.run_command("who --count", ensure_user=True)
        # Number of users before login would be 0 and after login would be 180
        # If below assertion would fail result_after_login is also 0, denoting login failed
        assert (result_before_login.output.split('=')[-1].strip() <
             result_after_login.output.split('=')[-1].strip()), "Login Failed"

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

    vm_console.wait_for_text(text_to_find=provider.data.templates.get('console_template')
        ['prompt_text'], timeout=200)

    with ssh.SSHClient(hostname=vm_obj.ip_address, username=console_vm_username,
            password=console_vm_password) as vm_ssh_client:
        # create file on system
        vm_console.send_keys("touch blather\n")
        wait_for(func=lambda: vm_ssh_client.run_command("ls blather", ensure_user=True) == 0,
            delay=1, num_sec=10)
        # if file was created in previous steps it will be removed here
        # we will get instance of SSHResult
        # Sometimes Openstack drops characters from word 'blather' hence try to remove
        # file using partial file name. Known issue, being worked on.
        command_result = vm_ssh_client.run_command("rm blather", ensure_user=True)
        assert command_result
