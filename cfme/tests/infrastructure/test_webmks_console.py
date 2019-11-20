"""Test for WebMKS Remote Consoles of VMware Providers."""

import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.generators import random_vm_name
from cfme.utils.providers import ProviderFilter


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[VMwareProvider],
                                                 required_flags=['webmks_console'])],
                         scope='module'),
]


@pytest.fixture(scope="function")
def vm_obj(appliance, provider, setup_provider, console_template):
    """VM creation/deletion fixture.

    Create a VM on the provider with the given template, and return the vm_obj.

    Clean up VM when test is done.
    """
    vm_obj = appliance.collections.infra_vms.instantiate(random_vm_name('webmks'),
                                                         provider,
                                                         console_template.name)
    vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip="default")
    yield vm_obj

    vm_obj.cleanup_on_provider()


@test_requirements.webmks
def test_webmks_vm_console(request, appliance, provider, vm_obj, configure_websocket,
        configure_console_webmks, take_screenshot):
    """Test the VMware WebMKS console support for a particular provider.

    The supported providers are:
        VMware vSphere6 and vSphere6.5

    For a given provider, and a given VM, the console will be opened, and then:

        - The console's status will be checked.
        - A command that creates a file will be sent through the console.
        - Using ssh we will check that the command worked (i.e. that the file
          was created.)

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
    """
    vm_obj.open_console(console='VM Console', invokes_alert=True)
    assert vm_obj.vm_console, 'VMConsole object should be created'
    vm_console = vm_obj.vm_console

    request.addfinalizer(vm_console.close_console_window)
    request.addfinalizer(appliance.server.logout)
    try:
        assert vm_console.wait_for_connect(180), "VM Console did not reach 'connected' state"
        assert vm_console.get_screen_text() != '', "VM Console screen text returned Empty"
        assert vm_console.send_fullscreen(), ("VM Console Toggle Full Screen button does not work")
    except Exception:
        # Take a screenshot if an exception occurs
        vm_console.switch_to_console()
        take_screenshot("ConsoleScreenshot")
        vm_console.switch_to_appliance()
        raise


@pytest.mark.manual('manualonly')
@test_requirements.webmks
@pytest.mark.tier(2)
@pytest.mark.parametrize('browser', ['chrome_latest', 'firefox_latest'])
@pytest.mark.parametrize('operating_system', ['fedora_latest', 'rhel8.x', 'rhel7.x', 'rhel6.x'])
def test_webmks_console_linux(browser, operating_system, provider):
    """
    This testcase is here to reflect testing matrix for webmks consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 2h
        caseimportance: high
        setup:
            1. Login to CFME Appliance as admin.
            2. On top right click Administrator|EVM -> Configuration.
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
            4. Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
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
@test_requirements.webmks
@pytest.mark.tier(2)
@pytest.mark.parametrize('browser', ['edge', 'internet_explorer'])
@pytest.mark.parametrize('operating_system', ['windows7', 'windows10',
 'windows_server2012', 'windows_server2016'])
def test_webmks_console_windows(browser, operating_system, provider):
    """
    This testcase is here to reflect testing matrix for webmks consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 2h
        caseimportance: high
        setup:
            1. Login to CFME Appliance as admin.
            2. On top right click Administrator|EVM -> Configuration.
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
            4. Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
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
@test_requirements.webmks
@pytest.mark.tier(1)
def test_webmks_console_passwordwithspecialchars():
    """
    VMware WebMKS Remote Console Test; password with special characters

    Bugzilla:
        1545927

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/3h
        setup: On CFME Appliance do the following:
               1) Login to CFME Appliance as admin.
               2) On top right click Administrator|EVM -> Configuration.
               3) Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware WebMKS".
               4) Click save at the bottom of the page.
               This will setup your appliance for using VMware WebMKS Console and not
               to use VMRC Plug in which is Default when you setup appliance.
        startsin: 5.8
    """
    pass
