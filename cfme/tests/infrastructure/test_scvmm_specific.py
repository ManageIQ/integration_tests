# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.scvmm import SCVMMProvider


pytestmark = [
    pytest.mark.provider([SCVMMProvider], scope="module"),
    pytest.mark.usefixtures("setup_provider_modscope")
]


@pytest.fixture
def testing_vm_without_dvd(provider, small_template):
    vm_name = "test_no_dvd_{}".format(fauxfactory.gen_alpha())
    vm = provider.appliance.collections.infra_vms.instantiate(
        vm_name, provider, small_template.name)
    vm.create_on_provider()
    vm.mgmt.disconnect_dvd_drives()
    yield vm
    vm.cleanup_on_provider()


@pytest.mark.tier(0)
def test_no_dvd_ruins_refresh(provider, testing_vm_without_dvd):
    """
    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Infra
        caseimportance: high
    """
    provider.refresh_provider_relationships()
    testing_vm_without_dvd.wait_to_appear()


@pytest.mark.manual
@pytest.mark.tier(2)
def test_template_info_scvmm():
    """
    The purpose of this test is to verify that the same number of
    templates in scvmm are in cfme.  Take the time to spot check a random
    template and check that the details correspond to SCVMM details.

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
        testSteps:
            1. Add SCVMM as a provider to CFME
            2. View templates for SCVMM in CFME
        expectedResults:
            1.
            2. Templates in VMM should match those in CFME
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vm_mac_scvmm():
    """
    Bugzilla:
        1514461

    Test case covers this BZ - we can"t get MAC ID of VM at the moment

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/20h
        testSteps:
            1. Add SCVMM to CFME
            2. Navigate to the details page of a VM (e.g. cu-24x7)
        expectedResults:
            1.
            2. MAC Address should match what is in SCVMM
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_create_appliance_on_scvmm_using_the_vhd_image():
    """
    View the documentation at access.redhat.com for help with this.

    Polarion:
        assignee: jdupuy
        casecomponent: Appliance
        initialEstimate: 1/4h
        subtype1: usability
        title: Create Appliance on SCVMM using the VHD image.
        upstream: yes
        testSteps:
            1. Download VHD image from http://file.cloudforms.lab.eng.rdu2.redhat.com/builds/cfme/
            2. Attach disk and deploy template
        expectedResults:
            1.
            2. CFME should be running in SCVMM
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provider_summary_scvmm():
    """
    The purpose of this test is to verify that the information on the
    provider summary is substantially the same as what is on SCVMM.
    Note: when automated this test will likely be broken up into many tests.

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.4
        testSteps:
            1. Add SCVMM as a provider in SCVMM
            2. Navigate to the provider summary page
            3. Click some of the links on this page
        expectedResults:
            1.
            2. Information on the provider summary page should match what is in SCVMM UI
            3. Links should go to the proper destination
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_host_info_scvmm():
    """
    Testing to make sure that the host info is correct in CFME

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.10
        testSteps:
            1. Add SCVMM as a provider in CFME
            2. Navigate to infra->hosts page
        expectedResults:
            1.
            2. All hosts should be present and information should be correct
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_check_disk_allocation_size_scvmm():
    """
    Test datastore used space is the correct value, c.f.
        https://github.com/ManageIQ/manageiq-providers-scvmm/issues/17
    Note, may have to edit settings on hyper-v host for checkpoint type:
        if set to production, try setting to standard

    Bugzilla:
        1490440

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        title: Check disk allocation size [SCVMM]
        testSteps:
            1. Provision VM and check it's "Total Datastore Used Space"
            2. go to VMM and create Vm's Checkpoint
            3. open VM Details check - "Total Datastore Used Space"
        expectedResults:
            1.
            2.
            3. The value should match what is in SCVMM
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_vm_volume_specchar1_scvmm():
    """
    Special Test to verify that VMs that have Volumes with no drive letter
    assigned don"t cause systemic SCVMM provider errors.  This is a low
    priority test.

    Bugzilla:
        1353285

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/4h
        startsin: 5.6.1
        upstream: no
    """
    pass
