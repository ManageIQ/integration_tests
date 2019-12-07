"""Test for HTML5 Remote Consoles of VMware/RHEV/RHOSP Providers."""
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.myservice import MyService
from cfme.utils.appliance import ViaSSUI
from cfme.utils.wait import wait_for


@pytest.mark.parametrize('context', [ViaSSUI])
@test_requirements.html5
@pytest.mark.provider([OpenStackProvider, VMwareProvider, RHEVMProvider],
    required_fields=['provisioning'])
@pytest.mark.uncollectif(lambda provider, appliance:
    (provider.one_of(VMwareProvider) and provider.version >= 6.5 and appliance.version < '5.11') or
    (provider.one_of(RHEVMProvider) and provider.version < 4.3),
    reason='VNC Not supported for CFME 5.10 with VMware 6.5 onward')
@pytest.mark.parametrize('order_service', [{'console_test': True}], indirect=True)
def test_vm_console_ssui(request, appliance, setup_provider, provider, context,
     configure_console_webmks, configure_console_vnc, order_service, take_screenshot,
     configure_websocket, console_template):
    """Test Myservice VM Console in SSUI.

    Metadata:
        test_flag: ssui

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
    """
    if provider.one_of(VMwareProvider) and appliance.version < '5.11':
        appliance.server.settings.update_vmware_console({'console_type': 'VNC'})
        request.addfinalizer(lambda: appliance.server.settings.update_vmware_console(
            {'console_type': 'VMware VMRC Plugin'}))
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
            # wait for screen text to return non-empty string, which implies console is loaded
            # and has readable text
            wait_for(func=lambda: vm_console.get_screen_text() != '', delay=5, timeout=45)
            assert vm_console.get_screen_text(), "VM Console screen text returned Empty"
        except Exception:
            # Take a screenshot if an exception occurs
            vm_console.switch_to_console()
            take_screenshot("ConsoleScreenshot")
            vm_console.switch_to_appliance()
            raise


@pytest.mark.manual('manualonly')
@test_requirements.html5
@pytest.mark.tier(2)
@pytest.mark.parametrize('browser', ['chrome_latest', 'firefox_latest'])
@pytest.mark.parametrize('operating_system', ['fedora_latest', 'rhel8.x', 'rhel7.x', 'rhel6.x'])
@pytest.mark.provider([OpenStackProvider, VMwareProvider, RHEVMProvider])
@pytest.mark.uncollectif(lambda provider, appliance:
    (provider.one_of(VMwareProvider) and provider.version >= 6.5 and appliance.version < '5.11') or
    (provider.one_of(RHEVMProvider) and provider.version < 4.3),
    reason='VNC Not supported for CFME 5.10 with VMware 6.5 onward')
def test_html5_ssui_console_linux(appliance, browser, operating_system, provider):
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
@pytest.mark.provider([OpenStackProvider, VMwareProvider, RHEVMProvider])
@pytest.mark.uncollectif(lambda provider, appliance:
    (provider.one_of(VMwareProvider) and provider.version >= 6.5 and appliance.version < '5.11') or
    (provider.one_of(RHEVMProvider) and provider.version < 4.3),
    reason='VNC Not supported for CFME 5.10 with VMware 6.5 onward')
def test_html5_ssui_console_windows(appliance, browser, operating_system, provider):
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
