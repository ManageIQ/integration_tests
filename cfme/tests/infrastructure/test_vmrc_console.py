import pytest

from cfme import test_requirements


@test_requirements.vmrc
@pytest.mark.manual
def test_vmrc_console_matrix():
    """
    This testcase is here to reflect testing matrix for vmrc consoles. Combinations listed
    are being tested manually. Originally, there was one testcase for every combination, this
    approach reduces number of needed testcases.

    Testing matrix:
        Systems:
            - fedora latest
            - rhel 6.x
            - rhel 7.x
            - windows 2012
            - windows 7
            - windows 10
        Browsers:
            - firefox latest
            - chrome latest
            - edge latest
            - explorer 11
        Providers:
            - vsphere 6
            - vsphere 65
            - vsphere 67

    Importance:
        High:
            - fedora latest + firefox, chrome + vsphere 67
            - rhel 7.x + firefox, chrome + vsphere 67
            - windows 10 + firefox, chrome, edge + vsphere 67
        Medium:
            - everything else

    Testcases:
        - test_vmrc_console_firefox_vsphere67_rhel6x
        - test_vmrc_console_firefox_vsphere67_rhel7x
        - test_vmrc_console_firefox_vsphere67_fedora
        - test_vmrc_console_firefox_vsphere67_win10
        - test_vmrc_console_firefox_vsphere67_win2012
        - test_vmrc_console_firefox_vsphere67_win7
        - test_vmrc_console_firefox_vsphere65_win7
        - test_vmrc_console_firefox_vsphere65_rhel7x
        - test_vmrc_console_firefox_vsphere65_fedora
        - test_vmrc_console_firefox_vsphere65_rhel6x
        - test_vmrc_console_firefox_vsphere65_win2012
        - test_vmrc_console_firefox_vsphere65_win10
        - test_vmrc_console_firefox_vsphere6_fedora
        - test_vmrc_console_firefox_vsphere6_win10
        - test_vmrc_console_firefox_vsphere6_win7
        - test_vmrc_console_firefox_vsphere6_rhel6x
        - test_vmrc_console_firefox_vsphere6_rhel7x
        - test_vmrc_console_firefox_vsphere6_win2012
        - test_vmrc_console_chrome_vsphere67_win10
        - test_vmrc_console_chrome_vsphere67_rhel7x
        - test_vmrc_console_chrome_vsphere67_win7
        - test_vmrc_console_chrome_vsphere67_fedora
        - test_vmrc_console_chrome_vsphere67_win2012
        - test_vmrc_console_chrome_vsphere65_rhel7x
        - test_vmrc_console_chrome_vsphere65_win10
        - test_vmrc_console_chrome_vsphere65_fedora
        - test_vmrc_console_chrome_vsphere65_win2012
        - test_vmrc_console_chrome_vsphere65_win7
        - test_vmrc_console_chrome_vsphere6_win2012
        - test_vmrc_console_chrome_vsphere6_win7
        - test_vmrc_console_chrome_vsphere6_rhel7x
        - test_vmrc_console_chrome_vsphere6_win10
        - test_vmrc_console_chrome_vsphere6_fedora
        - test_vmrc_console_edge_vsphere67_win10
        - test_vmrc_console_edge_vsphere65_win10
        - test_vmrc_console_edge_vsphere6_win10
        - test_vmrc_console_ie11_vsphere67_win7
        - test_vmrc_console_ie11_vsphere67_win2012
        - test_vmrc_console_ie11_vsphere65_win7
        - test_vmrc_console_ie11_vsphere65_win2012
        - test_vmrc_console_ie11_vsphere6_win2012
        - test_vmrc_console_ie11_vsphere6_win7

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


@pytest.mark.manual
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
