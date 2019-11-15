"""Test for HTML5 Remote Consoles of VMware/RHEV/RHOSP Providers."""
import imghdr
import re
import time

import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import providers
from cfme.services.myservice import MyService
from cfme.utils import ssh
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.net import wait_pingable
from cfme.utils.providers import ProviderFilter


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[CloudProvider, InfraProvider],
                                                 required_flags=['html5_console'])],
                         scope='module'),
]


@pytest.fixture(scope="function")
def vm_obj(request, provider, setup_provider, console_template):
    """
    Create a VM on the provider with the given template, and return the vm_obj.

    Cleanup VM when done
    """
    collection = provider.appliance.provider_based_collection(provider)
    vm_obj = collection.instantiate(random_vm_name('html5-con'),
                                    provider,
                                    template_name=console_template.name)

    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip="default")
    if provider.one_of(OpenStackProvider):
        # Assign FloatingIP to Openstack Instance from pool
        # so that we can SSH to it
        public_net = provider.data['public_network']
        vm_obj.mgmt.assign_floating_ip(public_net)
    return vm_obj


@pytest.mark.rhv1
@test_requirements.html5
def test_html5_vm_console(appliance, provider, configure_websocket, vm_obj,
        configure_console_vnc, take_screenshot):
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
    In the latest 5.11 build, for VMware, if VNC is not available for a VM, CFME Falls forward to
    WebMKS. To avoid that from happening, make sure your VM(.vmx)/Template(.vmtx) file
    has following two lines in it:

    RemoteDisplay.vnc.enabled = "true"
    RemoteDisplay.vnc.port = "5900"

    If not for above lines, Console may fall forward to WebMKS which is not something we
    want in this test case.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/4h
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

        if provider.one_of(VMwareProvider):
            # does have some text displayed and it is correct type of console is all we will do.
            assert vm_console.console_type == 'VNC', ("Wrong console type:"
            " looking for VNC found {}".format(vm_console.console_type))
        # wait for screen text to return non-empty string, which implies console is loaded
        # and has readable text
        wait_for(func=lambda: vm_console.get_screen_text() != '', delay=5, timeout=45)
        # Ensure pingable IP is present before trying console operations for reliability
        wait_pingable(vm_obj.mgmt, allow_ipv6=False, wait=300)
        assert vm_console.wait_for_text(text_to_find="login:", timeout=200), ("VM Console"
        " didn't prompt for Login")

        # Enter Username:
        vm_console.send_keys(console_vm_username)
        # find only "Pass" as sometime tessaract reads "w" as "u" and fails
        assert vm_console.wait_for_text(text_to_find="Pass", timeout=200), ("VM Console"
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
            # .split('\n')[-1] splits the console text on '\n' & picks last item of the list
            result = regex_for_login_password.findall(vm_console.get_screen_text()
                .split('\n')[-1])
            return result == []

        # if _validate_login() returns True, it means we did not find any of words
        # [login, password, incorrect] on last line of console text, which implies login success
        wait_for(func=_validate_login, timeout=300, delay=5)

        logger.info("Wait to get the '$' prompt")
        if provider.one_of(VMwareProvider):
            vm_console.wait_for_text(text_to_find=provider.data.templates
                .get('console_template')['prompt_text'], timeout=200)
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
                "CTRL+ALT+DEL key combination and CTRL+ALT+DEL button on HTML5 Console works.")
            assert vm_console.wait_for_text(text_to_find="login:", timeout=200), ("VM Console"
                " didn't prompt for Login")

        if not provider.one_of(OpenStackProvider):
            assert vm_console.send_fullscreen(), ("VM Console Toggle Full Screen button does"
            " not work")

        # Ensure VM had pingable IP before attempting SSH
        wait_pingable(vm_obj.mgmt, allow_ipv6=False, wait=300)
        with ssh.SSHClient(hostname=vm_obj.ip_address, username=console_vm_username,
                password=console_vm_password) as ssh_client:
            # if file was created in previous steps it will be removed here
            # we will get instance of SSHResult
            # Sometimes Openstack drops characters from word 'blather' hence try to remove
            # file using partial file name. Known issue, being worked on.
            command_result = ssh_client.run_command("rm blather", ensure_user=True)
            assert command_result
    except Exception:
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


@pytest.mark.tier(2)
@test_requirements.html5
@pytest.mark.provider([VMwareProvider], selector=ONE)
def test_html5_console_ports_present(appliance, provider):
    """
    Bugzilla:
        1514594

    Check to see if the Add/Edit provider screen has the Host VNC Start Port
    and Host VNC End port. Only applicable to versions of VMware that support VNC console.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/4h
        startsin: 5.8
    """
    edit_view = navigate_to(provider, 'Edit')
    assert edit_view.vnc_start_port.is_displayed
    assert edit_view.vnc_end_port.is_displayed


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
@pytest.mark.parametrize('browser', ['chrome_latest', 'firefox_latest'])
@pytest.mark.parametrize('operating_system', ['fedora_latest', 'rhel8.x', 'rhel7.x', 'rhel6.x'])
def test_html5_console_linux(browser, operating_system, provider):
    """
    This testcase is here to reflect testing matrix for html5 consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Login to CFME Appliance as admin.
            2. On top right click Administrator|EVM -> Configuration.
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
            4. Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
            5. Provision a testing VM.
        testSteps:
            1. Navigate to testing VM
            2. Launch the console by Access -> VM Console
            3. Make sure the console accepts commands
            4. Make sure the characters are visible
        expectedResults:
            1. VM Details displayed
            2. Console launched
            3. Console accepts characters
            4. Characters not garbled; no visual defect
    """
    pass


@pytest.mark.manual('manualonly')
@test_requirements.html5
@pytest.mark.tier(2)
@pytest.mark.parametrize('browser', ['edge', 'internet_explorer'])
@pytest.mark.parametrize('operating_system', ['windows7', 'windows10',
 'windows_server2012', 'windows_server2016'])
def test_html5_console_windows(browser, operating_system, provider):
    """This testcase is here to reflect testing matrix for html5 consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Login to CFME Appliance as admin.
            2. On top right click Administrator|EVM -> Configuration.
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
            4. Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
            5. Provision a testing VM.
        testSteps:
            1. Navigate to testing VM
            2. Launch the console by Access -> VM Console
            3. Make sure the console accepts commands
            4. Make sure the characters are visible
        expectedResults:
            1. VM Details displayed
            2. Console launched
            3. Console accepts characters
            4. Characters not garbled; no visual defect
    """
    pass


@pytest.mark.manual('manualonly')
@test_requirements.html5
@pytest.mark.tier(2)
@pytest.mark.parametrize('browser', ['chrome_latest', 'firefox_latest'])
@pytest.mark.parametrize('operating_system', ['fedora_latest', 'rhel8.x', 'rhel7.x', 'rhel6.x'])
def test_html5_ssui_console_linux(browser, operating_system, provider):
    """
    This testcase is here to reflect testing matrix for html5 consoles going via ssui.
    Combinations listed are being tested manually. Originally, there was one testcase for every
    combination, this approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup:
            1. Login to CFME Appliance as admin.
            2. On top right click Administrator|EVM -> Configuration.
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
            4. Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
            6. Create a service dialog and catalog that provisions a VM
        testSteps:
            1. Via ssui, order the catalog and wait for VM provision
            2. Via ssui, navigate to service details and click on
                Access-> VM Console for testing VM
            3. Make sure the console accepts commands
            4. Make sure the characters are visible
        expectedResults:
            1. Catalog ordered; VM provisioned
            3. Console accepts characters
            4. Characters not garbled; no visual defect
    """
    pass


@pytest.mark.manual('manualonly')
@test_requirements.html5
@pytest.mark.tier(2)
@pytest.mark.parametrize('browser', ['edge', 'internet_explorer'])
@pytest.mark.parametrize('operating_system', ['windows7', 'windows10',
    'windows_server2012', 'windows_server2016'])
def test_html5_ssui_console_windows(browser, operating_system, provider):
    """
    This testcase is here to reflect testing matrix for html5 consoles going via ssui.
    Combinations listed are being tested manually. Originally, there was one testcase for every
    combination, this approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 2/3h
        setup:
            1. Login to CFME Appliance as admin.
            2. On top right click Administrator|EVM -> Configuration.
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VNC".
            4. Click save at the bottom of the page.
               This will setup your appliance for using HTML5 VNC Console and not to
               use VMRC Plug in which is Default when you setup appliance.
            6. Create a service dialog and catalog that provisions a VM
        testSteps:
            1. Via ssui, order the catalog and wait for VM provision
            2. Via ssui, navigate to service details and click on
                Access-> VM Console for testing VM
            3. Make sure the console accepts commands
            4. Make sure the characters are visible
        expectedResults:
            1. Catalog ordered; VM provisioned
            3. Console accepts characters
            4. Characters not garbled; no visual defect
    """
    pass


@pytest.mark.parametrize('context', [ViaSSUI])
@test_requirements.html5
@pytest.mark.provider(gen_func=providers, filters=[ProviderFilter(
    classes=[OpenStackProvider, VMwareProvider, RHEVMProvider])])
@pytest.mark.parametrize('order_service', [['console_test']], indirect=True)
def test_vm_console_ssui(request, appliance, setup_provider, context, configure_websocket,
        configure_console_vnc, configure_console_webmks, order_service, take_screenshot,
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
    if (provider.one_of(VMwareProvider) and provider.version >= 6.5 and appliance.version <
            '5.11'):
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
                assert vm_console.wait_for_text(text_to_find="Pass", timeout=200), ("VM Console"
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
                        if not provider.one_of(OpenStackProvider):
                            return (user_count_before_login.output.split('=')[1][0] <
                                user_count_after_login.output.split('=')[1][0])
                        # for OSP Cirros image, user 'cirros' shows up in `who` output post
                        # login to vm console is successful, `who` command does not provide
                        # any count based output that we can compare, hence comparing output
                        # for username works best
                        return (console_vm_username not in user_count_before_login.output and
                            console_vm_username in user_count_after_login.output)
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
