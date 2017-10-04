# -*- coding: utf-8 -*-
"""Test for WebMKS Remote Consoles of VMware Providers."""
import imghdr
import pytest

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


@pytest.mark.uncollectif(lambda: version.current_version() < '5.8', reason='Only valid for >= 5.8')
def test_webmks_vm_console(request, appliance, provider, vm_obj,
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
        # Get the login screen image, and make sure it is a jpeg file:
        screen = vm_console.get_screen(180)
        assert imghdr.what('', screen) == 'jpeg'

        assert vm_console.wait_for_text(text_to_find="login:", timeout=200),\
            "VM Console didn't prompt for Login"

        result_before_login = ssh_client.run_command("who --count", ensure_user=True)
        # Enter Username:
        vm_console.send_keys(console_vm_username)

        assert vm_console.wait_for_text(text_to_find="Password", timeout=200),\
            "VM Console didn't prompt for Password"
        # Enter Password:
        vm_console.send_keys("{}\n".format(console_vm_password))

        result_after_login = ssh_client.run_command("who --count", ensure_user=True)
        # Number of users before login would be 0 and after login would be 180
        # If below assertion would fail result_after_login is also 0, denoting login failed
        assert (result_before_login.output.split('=')[-1].strip() <
             result_after_login.output.split('=')[-1].strip()), "Login Failed"

        logger.info("Wait to get the '$' prompt")

        vm_console.wait_for_text(text_to_find=provider.data.templates.get('console_template')
            ['prompt_text'], timeout=200)

        # create file on system
        vm_console.send_keys("touch blather\n")
        wait_for(func=ssh_client.run_command, func_args=["ls blather"],
            func_kwargs={'ensure_user': True},
            fail_condition=lambda result: result.rc != 0, delay=1, num_sec=10)
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
