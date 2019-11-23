"""Test for HTML5 Remote Consoles of VMware/RHEV/RHOSP Providers."""
import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.services.myservice import MyService
from cfme.utils.appliance import ViaSSUI
from cfme.utils.providers import ProviderFilter


@pytest.mark.parametrize('context', [ViaSSUI])
@pytest.mark.usefixtures('setup_provider')
@test_requirements.html5
@pytest.mark.provider(gen_func=providers, filters=[
    ProviderFilter(classes=[OpenStackProvider, VMwareProvider, RHEVMProvider])])
@pytest.mark.uncollectif(lambda provider, appliance:
    (provider.one_of(VMwareProvider) and provider.version >= 6.5 and appliance.version < '5.11') or
    (provider.one_of(RHEVMProvider) and provider.version < 4.3),
    reason='VNC Not supported for CFME 5.10 with VMware 6.5 onward')
@pytest.mark.parametrize('order_service', [['console_test']], indirect=True)
def test_vm_console_ssui(request, appliance, provider, context, configure_console_webmks,
        configure_console_vnc, order_service, take_screenshot, configure_websocket,
        console_template):
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
            assert vm_console.get_screen_text() != '', "VM Console screen text returned Empty"
        except Exception:
            # Take a screenshot if an exception occurs
            vm_console.switch_to_console()
            take_screenshot("ConsoleScreenshot")
            vm_console.switch_to_appliance()
            raise
