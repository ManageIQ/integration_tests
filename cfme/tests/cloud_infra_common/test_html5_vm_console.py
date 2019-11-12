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
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils import ssh
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
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


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_disabled():
    """
    For all versions of CFME 5.7 onward, VNC console should be Disabled
    for vsphere65 in OPSUI and SSUI

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseposneg: negative
        initialEstimate: 1h
        startsin: 5.7
        testSteps:
            1. Select VMware Console Support to VNC in CFME and Try to
               Access VM Console in OPS UI
            2. Create a Service to provision VM on vSphere65, open SUI,
               provision service, select provisioned service, On details
               page, try to access VM Console
        expectedResults:
            1. VM Console button is disabled
            2. VM Console is disabled
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_ports():
    """
    Negative port number should fail to open console

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartport5955_endportblank():
    """
    Should open connections for VNC port starting 5955 and keep opening
    until ports exhausted.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_html5_console_ports_present():
    """
    Bugzilla:
        1514594

    Check to see if the Add provider screen has the Host VNC Start Port
    and Host VNC End port.

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartportblank_endport5901():
    """
    Should open connections for VNC port starting 5900 and end at 5901

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartport5900_endport5902():
    """
    HTML5 tests have Host VNC start and End port settings now in Add
    VMware provider section, specifying the port range limits number of
    Consoles that can be opened simultaneously.We need to check that
    End port - Start Port + 1 = Number of Connections(console) that can be
    opened

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_rhv():
    """
    Bugzilla:
        1573739

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartport5955_endport5956():
    """
    HTML5 tests have Host VNC start and End port settings now in Add
    VMware provider section, specifying the port range limits number of
    Consoles that can be opened simultaneously.We need to check that
    End port - Start Port + 1 = Number of Connections(console) that can be
    opened

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_vncstartportblank_endportblank():
    """
    Both Start and End ports are blank. So Console will start opening with
    port 5900 and you can open consoles until ports are exhausted.
    UPDATE: I think console is going to be opened on
    port_that_was_last_used + 1. This means it won"t always be 5900.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_html5_console_check_consistency_of_behavior():
    """
    Bugzilla:
        1525692

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 3/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_console_matrix():
    """
    This testcase is here to reflect testing matrix for html5 consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Testing matrix:
        Systems:
            - fedora latest
            - rhel 6.x
            - rhel 7.x
            - windows 7
            - windows 2012
            - windows 10
        Browsers:
            - firefox latest
            - chrome latest
            - edge latest
            - explorer 11
        Providers:
            - vsphere 6
            - rhevm 4.2

    Importance:
        High:
            - fedora latest + firefox, chrome + vsphere6, rhevm42
            - rhel 7.x + firefox, chrome + vsphere6, rhevm42
            - windows 10 + firefox, chrome, edge + vsphere6, rhevm42
        Medium:
            - everything else

    Testcases:
        - test_html5_console_firefox_vsphere6_win2012
        - test_html5_console_firefox_vsphere6_win10
        - test_html5_console_firefox_vsphere6_rhel6x
        - test_html5_console_firefox_vsphere6_fedora
        - test_html5_console_firefox_vsphere6_win7
        - test_html5_console_firefox_vsphere6_rhel7x
        - test_html5_console_firefox_rhevm42_fedora_vnc
        - test_html5_console_firefox_rhevm42_fedora_spice
        - test_html5_console_chrome_vsphere6_fedora
        - test_html5_console_chrome_vsphere6_fedora
        - test_html5_console_chrome_vsphere6_win7
        - test_html5_console_chrome_vsphere6_rhel7x
        - test_html5_console_chrome_vsphere6_win10
        - test_html5_console_chrome_vsphere6_fedora
        - test_html5_console_chrome_vsphere6_win2012
        - test_html5_console_chrome_rhevm42_fedora_vnc
        - test_html5_console_chrome_rhevm42_fedora_spice
        - test_html5_console_edge_vsphere6_win10
        - test_html5_console_edge_rhevm42_win10_vnc
        - test_html5_console_edge_rhevm42_win10_spice
        - test_html5_console_ie11_vsphere6_win7
        - test_html5_console_ie11_vsphere6_win2012

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


@pytest.mark.manual
@test_requirements.html5
@pytest.mark.tier(2)
def test_html5_ssui_console_matrix():
    """
    This testcase is here to reflect testing matrix for html5 consoles going via ssui.
    Combinations listed are being tested manually. Originally, there was one testcase for every
    combination, this approach reduces number of needed testcases.

    Testing matrix:
        Systems:
            - fedora latest
            - rhel
            - windows 7
            - windows 10
        Browsers:
            - firefox latest
            - chrome latest
            - edge latest
            - explorer 11
        Providers:
            - vsphere 6
            - rhevm 4.2


    Importance:
        High:
            - fedora latest + firefox, chrome + vsphere6, rhevm42
            - rhel 7.x + firefox, chrome + vsphere6, rhevm42
            - windows 10 + firefox, chrome, edge + vsphere6, rhevm42
        Medium:
            - everything else

    Testcases:
        - test_html5_console_firefox_ssui_rhel
        - test_html5_console_firefox_ssui_win7
        - test_html5_console_firefox_ssui_fedora
        - test_html5_console_firefox_ssui_win10
        - test_html5_console_chrome_ssui_fedora
        - test_html5_console_chrome_ssui_rhel
        - test_html5_console_chrome_ssui_win7
        - test_html5_console_ie11_ssui_win7
        - test_html5_console_edge_ssui_win10
        - test_html5_console_vsphere6_ssui

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
