"""Test for HTML5 Remote Consoles of VMware/RHEV/RHOSP Providers."""
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
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
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
    vm_obj.open_console(console='VM Console')
    assert vm_obj.vm_console, 'VMConsole object should be created'
    vm_console = vm_obj.vm_console
    try:
        # If the banner/connection-status element exists we can get
        # the connection status text and if the console is healthy, it should connect.
        assert vm_console.wait_for_connect(180), "VM Console did not reach 'connected' state"

        if provider.one_of(VMwareProvider):
            # does have some text displayed and it is correct type of console is all we will do.
            assert vm_console.console_type == 'VNC', ("Wrong console type:"
            " looking for VNC found {}".format(vm_console.console_type))
        # wait for screen text to return non-empty string, which implies console is loaded
        # and has readable text
        wait_for(func=lambda: vm_console.get_screen_text() != '', delay=5, timeout=45)
        assert vm_console.get_screen_text() != '', "VM Console screen text returned Empty"
        if not provider.one_of(OpenStackProvider):
            assert vm_console.send_fullscreen(), "VM Console Toggle Full Screen button doesn't work"
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
    with appliance.context.use(context):
        myservice = MyService(appliance, service_name)
        vm_obj = myservice.launch_vm_console(catalog_item)
        vm_console = vm_obj.vm_console
        if provider.one_of(OpenStackProvider):
            public_net = provider.data['public_network']
            vm_obj.mgmt.assign_floating_ip(public_net)
        request.addfinalizer(vm_console.close_console_window)
        request.addfinalizer(appliance.server.logout)
        try:
            assert vm_console.wait_for_connect(180), ("VM Console did not reach 'connected'"
                " state")
            assert vm_console.get_screen_text() != '', "VM Console screen text returned Empty"
        except Exception:
            # Take a screenshot if an exception occurs
            vm_console.switch_to_console()
            take_screenshot("ConsoleScreenshot")
            vm_console.switch_to_appliance()
            raise
