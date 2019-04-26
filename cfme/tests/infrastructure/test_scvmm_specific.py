# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ


pytestmark = [
    pytest.mark.provider([SCVMMProvider], scope="module"),
    pytest.mark.usefixtures("setup_provider_modscope"),
    test_requirements.scvmm
]


# conversion dict for sizes
SIZES = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}


@pytest.fixture
def vm(provider, small_template):
    vm_name = "test-scvmm-{}".format(fauxfactory.gen_alpha())
    vm = provider.appliance.collections.infra_vms.instantiate(
        vm_name, provider, small_template.name
    )
    vm.create_on_provider(find_in_cfme=True)
    yield vm
    vm.cleanup_on_provider()


@pytest.mark.tier(0)
def test_no_dvd_ruins_refresh(provider, vm):
    """
    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Infra
        caseimportance: high
    """
    vm.mgmt.disconnect_dvd_drives()
    provider.refresh_provider_relationships()
    vm.wait_to_appear()


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1514461])
def test_vm_mac_scvmm(provider):
    """
    Bugzilla:
        1514461

    Test case covers this BZ - we can't get MAC ID of VM at the moment

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
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.all()[0]
    # get mac address(es) from SCVMM
    mac_addresses = [entry["PhysicalAddress"] for entry in vm.mgmt.raw["VirtualNetworkAdapters"]]
    # get mac address(es) from CFME
    view = navigate_to(vm, "Details", use_resetter=False)
    try:
        mac_address = view.entities.summary('Properties').get_text_of("MAC Address")
    except NameError:
        # since some vms have plural 'Addresses'.
        mac_address = view.entities.summary('Properties').get_text_of("MAC Addresses")
    assert mac_address in mac_addresses


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
            1. Download VHD image
            2. Attach disk and deploy template
        expectedResults:
            1.
            2. CFME should be running in SCVMM
    """
    pass


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1700909)], automates=[1700909])
def test_check_disk_allocation_size_scvmm(vm):
    """
    Test datastore used space is the correct value, c.f.
        https://github.com/ManageIQ/manageiq-providers-scvmm/issues/17
    Note, may have to edit settings on hyper-v host for checkpoint type:
        if set to production, try setting to standard

    Bugzilla:
        1490440
        1700909

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
    view = navigate_to(vm, "Details")
    usage_before = view.entities.summary("Datastore Actual Usage Summary").get_text_of(
        "Total Datastore Used Space"
    )
    # create snapshot, note that this will set check_type to "Standard" by default
    vm.mgmt.create_snapshot()
    vm.refresh_relationships(from_details=True)
    view = navigate_to(vm, "Details", force=True)
    usage_after = view.entities.summary("Datastore Actual Usage Summary").get_text_of(
        "Total Datastore Used Space"
    )

    msg = "Usage before snapshot: {}, Usage after snapshot: {}".format(usage_before, usage_after)
    # convert usage after and before to bytes
    vb, kb = usage_before.split()
    va, ka = usage_after.split()
    usage_before = float(vb) * SIZES[kb]
    usage_after = float(va) * SIZES[ka]
    # we assert that the usage after should be greater than the usage before
    assert usage_after > usage_before, msg
    # also assert that the Snapshots usage is not 0
    usage_snapshots = view.entities.summary("Datastore Actual Usage Summary").get_text_of(
        "Snapshots"
    )
    assert usage_snapshots.split()[0] > 0


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
