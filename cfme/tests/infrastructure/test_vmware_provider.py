# -*- coding: utf-8 -*-
"""Manual VMware Provider tests"""
import pytest


@pytest.mark.manual
@pytest.mark.tier(3)
def test_vmware_provider_filters():
    """
    N-3 filters for esx provider.
    Example: ESXi 6.5 is the current new release.
    So filters for 6.7 (n), 6.5 (n-1), 6.0 (n-2) at minimum.

    Polarion:
        assignee: kkulkarn
        casecomponent: Provisioning
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1.Integrate VMware provider in CFME
            2.Go to Compute->Infrastructure->Hosts
            3.Try to use preset filters
        expectedResults:
            1.
            2.All hosts are listed.
            3.We should have at least 3 filters based on VMware version.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_appliance_scsi_control_vmware():
    """
    Appliance cfme-vsphere-paravirtual-*.ova has SCSI controller as Para
    Virtual

    Polarion:
        assignee: kkulkarn
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/4h
    #TODO: yet to test this, once done, I will add steps. Test was not written by me originally.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_vds_ui_display():
    """
    Virtual Distributed Switch port groups are displayed for VMs assigned
    to vds port groups.
    Compute > Infrastructure > Host > [Select host] > Properties > Network

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: integration
        testSteps:
            1.Integrate VMware provider in CFME
            2.Compute > Infrastructure > Host > [Select host] > Properties > Network
            3.Check if host has Distributed Switch and it is displayed on this page
        expectedResults:
            1.
            2.Properties page for the host opens.
            3.If DSwitch exists it will be displayed on this page.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_guests_linked_clone():
    """
    VMware guests are incorrectly marked as linked_clone true, remove attribute
    VMs are incorrectly marked as Linked Clones.
    Every VM discovered from VMware provider has "linked_clone": true.
    However, none of the VMs is sharing a disk or has a snapshot.
    Ideally they shouldn't mark them all as linked_clone=t

    Bugzilla:
        * 1588908

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/3h
        testtype: integration
        testSteps:
            1.Integrate VMware provider in CFME
            2.Check the total number of VMs present
            # psql -U postgres -d vmdb_production -c "select name from vms where vendor='vmware';" |
            wc -l
            3.Now, check the total number of VMs having linked_clone set as True:
            # psql -U postgres -d vmdb_production -c "select name from vms where vendor='vmware'
            and linked_clone='t';" | wc -l
        expectedResults:
            1.
            2.Should return VM count
            3.Should return VM count where linked_clone='t' and should be less than count in step2.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_reconfigure_vm_controller_type():
    """
    Edit any VM which is provisioned for vSphere and select "Reconfigure this VM" option.
    In "Controller Type" column we do not see the Controller Type listed.
    Controller Type should be listed.

    Bugzilla:
        * 1650441

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        testtype: integration
        title: Test Controller type is listed in "Reconfigure VM Disk" Controller Type Column
        testSteps:
            1.Integrate VMware provider in CFME
            2.Navigate to Compute->Infrastructure->Virtual Machines
            3.Select a virtual machine and select Configure->Reconfigure Selected Item
            4.Check if Disks table lists controller type
        expectedResults:
            1.
            2.
            3.Reconfigure VM opion should be enabled
            4.Controller type should be listed
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_vds_ui_tagging():
    """
    Virtual Distributed Switch port groups are displayed for VMs assigned
    to vds port groups. Check to see if you can navigate to DSwitch and tag it.
    Compute > Infrastructure > Host > [Select host] > Properties > Network

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
        testtype: integration
        testSteps:
            1.Integrate VMware provider in CFME
            2.Compute > Infrastructure > Host > [Select host] > Properties > Network
            3.Check if host has Distributed Switch and it is displayed on this page
            4.If displayed, try to select Policy->Assign Tag to DSwitch.
        expectedResults:
            1.
            2.Properties page for the host opens.
            3.If DSwitch exists it will be displayed on this page.
            4.You can assign tags to DSwitch.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_inaccessible_datastore():
    """
    VMware sometimes has datastores that are inaccessible, and CloudForms should indicate that.

    Bugzilla:
        * 1684656

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        testtype: integration
        testSteps:
            1.Integrate VMware provider in CFME
            2.Compute > Infrastructure > Datastores
            3.Check if any of the datastores marked inaccessible and compare it with VMware UI.
        expectedResults:
            1.
            2.Datastores page opens showing all the datastores known to CFME
            3.All datastores that are inaccessible in vSphere should be marked such in CFME UI too.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_cdrom_dropdown_not_blank():
    """
    Test CD/DVD Drives dropdown lists ISO files, dropdown is not blank

    Bugzilla:
        * 1689369

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        testtype: integration
        testSteps:
            1.Integrate VMware provider in CFME
            2.Compute > Infrastructure > Datastores
            3.Run SSA on datastore which contains ISO files
            4.Navigate to Compute>Infrastructure>Virtual Machines, select any virtual machine
            5.Reconfigure it to have new ISO file attached to it in CD/DVD drive
        expectedResults:
            1.
            2.Datastores page opens showing all the datastores known to CFME
            3.SSA runs successfully, and you can see files in datastore
            4.Virtual machine is selected
            5.Dropdown of ISO files is not empty for CD/DVD Drive
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_inaccessible_datastore_vm_provisioning():
    """
    VMware sometimes has datastores that are inaccessible, and CloudForms should not pick this
    during provisioning when using "Choose Automatically" as an option under environment tab.

    Bugzilla:
        * 1694137

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/4h
        testtype: integration
        testSteps:
            1.Integrate VMware provider in CFME
            2.Compute > Infrastructure > Virtual Machines > Templates
            3.Provision a VM from template, make sure to have at least 1 Datastore on VMware that is
              inaccssible & while provisioning use "Choose Automatically" option in Environment Tab.
        expectedResults:
            1.
            2.See all available templates
            3.CFME should provision VM on datastore other than the one that is inaccessible.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_provisioned_vm_host_relationship():
    """
    VMware VMs provisioned through cloudforms should have host relationship.

    Bugzilla:
        * 1657341

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/2h
        testtype: integration
        testSteps:
            1.Integrate VMware provider in CFME
            2.Compute > Infrastructure > Virtual Machines > Templates
            3.Provision a VM from template
        expectedResults:
            1.
            2.See all available templates
            3.CFME Provisioned VM should have host relationship.
    """
    pass
