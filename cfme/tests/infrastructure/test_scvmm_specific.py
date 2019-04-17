# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.scvmm import SCVMMProvider


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
@pytest.mark.meta(blockers=[1178961])
@pytest.mark.provider([SCVMMProvider], scope="module")
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
def test_template_info_scvmm2016():
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
    """
    pass


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
        initialEstimate: 1/4h
        startsin: 5.4
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
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1514461
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_create_appliance_on_scvmm_using_the_vhd_image():
    """
    Log into qeblade33 and download the VHD appliance image.  Create a new
    VM, attach the VHD disk, and boot system.

    Polarion:
        assignee: jdupuy
        casecomponent: Appliance
        initialEstimate: 1/4h
        subtype1: usability
        title: Create Appliance on SCVMM using the VHD image.
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provider_summary_scvmm2016():
    """
    The purpose of this test is to verify that the information on the
    provider summary is substantially the same as what is on SCVMM.
    Since SCVMM-2016 only has a short sequence of test cases, you must use
    this test case as the catch all to go in and spend 15-30 minutes and
    check as many links from this page and verify both the navigation and
    the content.

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provider_summary_scvmm():
    """
    The purpose of this test is to verify that the information on the
    provider summary is substantially the same as what is on SCVMM.
    Since SCVMM-SP1 only has a short sequence of test cases, you must use
    this test case as the catch all to go in and spend 15-30 minutes and
    check as many links from this page and verify both the navigation and
    the content.

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_host_info_scvmm():
    """
    The purpose of this test is to verify that SCVMM-SP1 hosts are not
    only added, but that the host information details are correct.  Take
    the time to spot check at least one host.

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.4
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_host_info_scvmm2016():
    """
    The purpose of this test is to verify that SCVMM-2016 hosts are not
    only added, but that the host information details are correct.  Take
    the time to spot check at least one host.

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.snapshot
@pytest.mark.tier(1)
def test_check_disk_allocation_size_scvmm():
    """
    Bugzilla:
        1490440

    Steps to Reproduce:
    1.Provision VM and check it"s "Total Datastore Used Space"
    2.go to VMM and create Vm"s Checkpoint
    3.open VM Details check - "Total Datastore Used Space"

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        title: Check disk allocation size [SCVMM]
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
