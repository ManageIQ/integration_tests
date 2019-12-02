import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider


@test_requirements.vmrc
@pytest.mark.provider([VMwareProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')])
def test_vmrc_console(request, appliance, setup_provider, provider, configure_console_vmrc):
    """
    Test VMRC console can be opened for the VMware provider.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 2h
        setup:
            1. Login to CFME Appliance as admin.
            2. Navigate to Configuration
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" & select "VMware VMRC Plugin"(Applicable to versions older than CFME 5.11).
            4. Click save at the bottom of the page.
            5. Provision a testing VM.
        testSteps:
            1. Navigtate to testing VM
            2. Launch the console by Access -> VM Console
        expectedResults:
            1. VM Details displayed
            2. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few seconds for the VMRC console.
    """
    vms_collections = appliance.collections.infra_vms
    vm = vms_collections.instantiate(name='cu-24x7', provider=provider)
    if not vm.exists_on_provider:
        pytest.skip("Skipping test, cu-24x7 VM does not exist")
    if appliance.version < '5.11':
        vm.open_console(console='VM Console', invokes_alert=True)
        assert vm.vm_console, 'VMConsole object should be created'
        request.addfinalizer(vm.vm_console.close_console_window)
    else:
        vm.open_console(console='VMRC Console', invokes_alert=True)
        assert vm.vm_console, 'VMConsole object should be created'
        request.addfinalizer(vm.vm_console.close_console_window)
    request.addfinalizer(appliance.server.logout)


@test_requirements.vmrc
@pytest.mark.manual("manualonly")
@pytest.mark.parametrize('browser', ['edge', 'internet_explorer'])
@pytest.mark.parametrize('operating_system', ['windows7', 'windows10',
 'windows_server2012', 'windows_server2016'])
@pytest.mark.provider([VMwareProvider])
def test_vmrc_console_windows(browser, operating_system, provider):
    """
    This testcase is here to reflect testing matrix for vmrc consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 2h
        setup:
            1. Login to CFME Appliance as admin.
            2. Navigate to Configuration
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware VMRC Plugin".
            4. Click save at the bottom of the page.
            5. Provision a testing VM.
        testSteps:
            1. Navigtate to testing VM
            2. Launch the console by Access -> VM Console
            3. Make sure the console accepts commands
            4. Make sure the characters are visible
        expectedResults:
            1. VM Details displayed
            2. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            3. Console accepts characters
            4. Characters not garbled; no visual defect
    """
    pass


@test_requirements.vmrc
@pytest.mark.manual("manualonly")
@pytest.mark.parametrize('browser', ['chrome_latest', 'firefox_latest'])
@pytest.mark.parametrize('operating_system', ['fedora_latest', 'rhel8.x', 'rhel7.x', 'rhel6.x'])
@pytest.mark.provider([VMwareProvider])
def test_vmrc_console_linux(browser, operating_system, provider):
    """
    This testcase is here to reflect testing matrix for vmrc consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 2h
        setup:
            1. Login to CFME Appliance as admin.
            2. Navigate to Configuration
            3. Under VMware Console Support section and click on Dropdown in front
               of "Use" and select "VMware VMRC Plugin".
            4. Click save at the bottom of the page.
            5. Provision a testing VM.
        testSteps:
            1. Navigtate to testing VM
            2. Launch the console by Access -> VM Console
            3. Make sure the console accepts commands
            4. Make sure the characters are visible
        expectedResults:
            1. VM Details displayed
            2. You should see a Pop-up being Blocked, Please allow it to
               open (always allow pop-ups for this site) and then a new tab
               will open and then in few secs, you will see a prompt asking
               you if you would like to open VMRC, click Yes. Once done,
               VMRC Window will open(apart from browser) and it will ask
               you if you would like to View Certificate or Connect anyway
               or Cancel, please click Connect Anyway. Finally, you should
               see VM in this window and should be able to interact with it
               using mouse/keyboard.
            3. Console accepts characters
            4. Characters not garbled; no visual defect
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_novmrccredsinprovider():
    """
    Leave the VMRC Creds blank in the provider add/edit dialog and observe
    behavior trying to launch console. It should fail. Also observe the
    message in VMRC Console Creds tab about what will happen if creds left
    blank.

    Bugzilla:
        1550612

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: critical
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_addremovevmwarecreds():
    """
    Add VMware VMRC Console Credentials to a VMware Provider and then
    Remove it.

    Bugzilla:
        1559957

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        initialEstimate: 1/4h
        startsin: 5.8
        testSteps:
            1. Compute->Infrastructure->Provider, Add VMware Provider with VMRC Console Creds
            2. Edit provider, remove VMware VMRC Console Creds and Save
        expectedResults:
            1. Provider added
            2. Provider can be Saved without VMRC Console Creds
    """
    pass


@pytest.mark.manual("manualonly")
@test_requirements.vmrc
@pytest.mark.tier(2)
def test_vmrc_console_usecredwithlimitedvmrcaccess():
    """
    Add Provider in VMware now has a new VMRC Console Tab for adding
    credentials which will be used to initiate VMRC Connections and these
    credentials could be less privileged as compared to Admin user but
    needs to have Console Access.
    In current VMware env we have "user_interact@vsphere.local" for this
    purpose. It is setup on vSphere65(NVC) and has no permissions to add
    network device, suspend vm, install vmware tools or reconfigure
    floppy. So if you can see your VMRC Console can"t do these operations
    with user_interact, mark this test as passed. As the sole purpose of
    this test is to validate correct user and permissions are being used.

    Bugzilla:
        1479840

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/2h
        startsin: 5.8
    """
    pass
