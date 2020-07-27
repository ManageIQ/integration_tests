"""This module tests various ways how to set up the provisioning using the provisioning dialog."""
import re
from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest
from widgetastic.utils import partial_match
from widgetastic_patternfly import CheckableBootstrapTreeview as CbTree

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common import BaseLoggedInPage
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


not_scvmm = ProviderFilter(classes=[SCVMMProvider], inverted=True)
all_infra = ProviderFilter(classes=[InfraProvider],
                           required_fields=[['provisioning', 'template'],
                                            ['provisioning', 'host'],
                                            ['provisioning', 'datastore']])

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.long_running,
    test_requirements.provision,
    pytest.mark.tier(3),
    pytest.mark.provider(gen_func=providers, scope="module",
                         filters=[ProviderFilter(required_flags=['provision'])])

]


def prov_source(provider):
    if provider.one_of(CloudProvider):
        return provider.data['provisioning']['image']['name']
    else:
        return provider.data['provisioning']['template']


@pytest.fixture(scope="function")
def vm_name():
    vm_name = random_vm_name('provd')
    return vm_name


@pytest.fixture(scope="function")
def prov_data(provisioning, provider):
    # TODO Perhaps merge this with stuff with test_cloud_init_provisioning.test_provision_cloud_init
    data = dict(provisioning, **{
        'request': {
            'email': fauxfactory.gen_email(),
            'first_name': fauxfactory.gen_alphanumeric(),
            'last_name': fauxfactory.gen_alphanumeric(),
            'manager_name': fauxfactory.gen_alphanumeric(20, start="manager ")},
        'catalog': {},
        'hardware': {},
        'schedule': {},
        'purpose': {},
    })

    mgmt_system = provider.mgmt

    if provider.one_of(InfraProvider):
        data['network'] = {'vlan': partial_match(provisioning.get('vlan'))}
        data['environment'] = {
            'datastore_name': {'name': provisioning['datastore']},
            'host_name': {'name': provisioning['host']}}
    elif provider.one_of(AzureProvider):
        data['environment'] = {'public_ip_address': "New"}
    elif provider.one_of(OpenStackProvider):
        ip_pool = provider.data['public_network']
        floating_ip = mgmt_system.get_first_floating_ip(pool=ip_pool)
        provider.refresh_provider_relationships()
        data['environment'] = {'public_ip_address': floating_ip}
        props = data.setdefault('properties', {})
        props['instance_type'] = partial_match(provisioning['ci-flavor-name'])

    if provider.one_of(RHEVMProvider):
        data['catalog']['provision_type'] = 'Native Clone'
    elif provider.one_of(VMwareProvider):
        data['catalog']['provision_type'] = 'VMware'
    # Otherwise just leave it alone
    return data


@pytest.fixture(scope="function")
def provisioner(appliance, request, setup_provider, provider, vm_name):

    def _provisioner(template, provisioning_data, delayed=None):
        collection = appliance.provider_based_collection(provider)
        provisioning_data['template_name'] = template
        provisioning_data['provider_name'] = provider.name
        vm = collection.create(vm_name, provider, form_values=provisioning_data)

        base_view = vm.appliance.browser.create_view(BaseLoggedInPage)
        base_view.flash.assert_no_error()

        request.addfinalizer(
            lambda: vm.cleanup_on_provider())
        request_description = f'Provision from [{template}] to [{vm_name}]'
        provision_request = appliance.collections.requests.instantiate(
            description=request_description)
        check_all_tabs(provision_request, provider)

        if delayed is not None:
            total_seconds = (delayed - datetime.utcnow()).total_seconds()
            try:
                wait_for(provision_request.is_finished,
                         fail_func=provision_request.update, num_sec=total_seconds, delay=5)
                pytest.fail("The provisioning was not postponed")
            except TimedOutError:
                pass

        logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider.key)
        wait_for(
            provider.mgmt.does_vm_exist, [vm_name],
            fail_func=provider.refresh_provider_relationships,
            handle_exception=True, num_sec=600
        )

        # nav to requests page happens on successful provision
        logger.info('Waiting for cfme provision request for vm %s', vm_name)
        provision_request.wait_for_request()
        msg = f"Provisioning failed with the message {provision_request.rest.message}"
        assert provision_request.is_succeeded(), msg
        return vm

    return _provisioner


def check_all_tabs(provision_request, provider):
    view = navigate_to(provision_request, "Details")

    for name in provider.provisioning_dialog_widget_names:
        widget = getattr(view, name)
        widget.click()
        assert widget.is_displayed


@pytest.mark.meta(blockers=[BZ(1627673, forced_streams=['5.10'])])
@pytest.mark.provider(gen_func=providers, filters=[all_infra], scope="module")
def test_change_cpu_ram(provisioner, soft_assert, provider, prov_data, vm_name):
    """ Tests change RAM and CPU in provisioning dialog.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set number of CPUs and amount of RAM.
        * Submit the provisioning request and wait for it to finish.
        * Visit the page of the provisioned VM. The summary should state correct values for CPU&RAM.

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    prov_data['catalog']["vm_name"] = vm_name
    prov_data['hardware']["num_sockets"] = "4"
    prov_data['hardware']["cores_per_socket"] = "1" if not provider.one_of(SCVMMProvider) else None
    prov_data['hardware']["memory"] = "2048"

    vm = provisioner(prov_source(provider), prov_data)

    # Go to the VM info
    view = navigate_to(vm, "Details")
    data = view.entities.summary("Properties").get_text_of("Container").strip()
    # No longer possible to use version pick because of cherrypicking?
    regexes = list(map(re.compile, [
        r"^[^(]*(\d+) CPUs?.*, ([^)]+)[^)]*$",
        r"^[^(]*\((\d+) CPUs?, ([^)]+)\)[^)]*$",
        r"^.*?(\d+) CPUs? .*?(\d+ MB)$"]))
    for regex in regexes:
        match = regex.match(data)
        if match is not None:
            num_cpus, memory = match.groups()
            break
    else:
        raise ValueError("Could not parse string {}".format(repr(data)))
    soft_assert(num_cpus == "4", "num_cpus should be {}, is {}".format("4", num_cpus))
    soft_assert(memory == "2048 MB", "memory should be {}, is {}".format("2048 MB", memory))


# Special parametrization in testgen above
@pytest.mark.meta(blockers=[1209847, 1380782], automates=[1633867])
@pytest.mark.provider(gen_func=providers,
                      filters=[all_infra, not_scvmm],
                      scope="module")
@pytest.mark.parametrize("disk_format", ["Thin", "Thick", "Preallocated",
    "Thick - Lazy Zero", "Thick - Eager Zero"],
    ids=["thin", "thick", "preallocated", "thick_lazy", "thick_eager"])
@pytest.mark.uncollectif(lambda provider, disk_format, appliance:
                         (provider.one_of(RHEVMProvider) and
                          disk_format in ["Thick", "Thick - Lazy Zero", "Thick - Eager Zero"]) or
                         (provider.one_of(VMwareProvider) and
                          disk_format == "Thick" and
                          appliance.version > '5.11') or
                         (provider.one_of(VMwareProvider) and
                          disk_format in ["Thick - Lazy Zero", "Thick - Eager Zero"] and
                          appliance.version < '5.11') or
                         (not provider.one_of(RHEVMProvider) and
                          disk_format == "Preallocated") or
                         # Temporarily, our storage domain cannot handle Preallocated disks
                         (provider.one_of(RHEVMProvider) and
                          disk_format == "Preallocated"),
                         reason='Invalid combination of disk format and provider type '
                                'or appliance version (or both!)')
def test_disk_format_select(provisioner, disk_format, provider, prov_data, vm_name):
    """ Tests disk format selection in provisioning dialog.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set the disk format to be thick or thin.
        * Submit the provisioning request and wait for it to finish.
        * Visit the page of the provisioned VM.
        * The ``Thin Provisioning Used`` field should state true of false according to the selection

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: high
        initialEstimate: 1/6h
    """

    prov_data['catalog']['vm_name'] = vm_name
    prov_data['hardware']["disk_format"] = disk_format

    vm = provisioner(prov_source(provider), prov_data)

    # Go to the VM info
    view = navigate_to(vm, 'Details')
    thin = view.entities.summary('Datastore Allocation Summary').get_text_of(
        'Thin Provisioning Used').strip().lower()
    vm.load_details(refresh=True)
    if disk_format == "Thin":
        assert thin == 'true', "The disk format should be Thin"
    else:
        assert thin != 'true', "The disk format should not be Thin"


@pytest.mark.parametrize("started", [True, False])
@pytest.mark.meta(automates=[1797706])
@pytest.mark.provider(gen_func=providers, filters=[all_infra], scope="module")
def test_power_on_or_off_after_provision(provisioner, prov_data, provider, started, vm_name):
    """ Tests setting the desired power state after provisioning.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set whether you want or not the VM to be
            powered on after provisioning.
        * Submit the provisioning request and wait for it to finish.
        * The VM should become steady in the desired VM power state.

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['schedule']["power_on"] = started

    vm = provisioner(prov_source(provider), prov_data)

    wait_for(
        lambda: vm.exists_on_provider and
        (vm.mgmt.is_running if started else vm.mgmt.is_stopped),
        num_sec=240, delay=5
    )


@test_requirements.tag
def test_tag(provisioner, prov_data, provider, vm_name):
    """ Tests tagging VMs using provisioning dialogs.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, pick a tag.
        * Submit the provisioning request and wait for it to finish.
        * Visit th page of VM, it should display the selected tags


    Metadata:
        test_flag: provision

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/8h
    """
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['purpose']["apply_tags"] = CbTree.CheckNode(path=("Service Level *", "Gold"))

    vm = provisioner(prov_source(provider), prov_data)

    tags = vm.get_tags()
    assert any(
        tag.category.display_name == "Service Level" and tag.display_name == "Gold"
        for tag in tags
    ), f"Service Level: Gold not in tags ({tags})"


@pytest.mark.meta(blockers=[1204115])
@test_requirements.scheduled_ops
def test_provisioning_schedule(provisioner, provider, prov_data, vm_name):
    """ Tests provision scheduling.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set a scheduled provision and pick a time.
        * Submit the provisioning request, it should not start before the scheduled time.

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    now = datetime.utcnow()
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['schedule']["schedule_type"] = "Schedule"
    prov_data['schedule']["provision_date"] = now.strftime("%m/%d/%Y")
    STEP = 5
    minutes_diff = (STEP - (now.minute % STEP))
    # To have some gap for automation
    if minutes_diff <= 3:
        minutes_diff += 5
    provision_time = timedelta(minutes=minutes_diff) + now
    prov_data['schedule']["provision_start_hour"] = str(provision_time.hour)
    prov_data['schedule']["provision_start_min"] = str(provision_time.minute)

    provisioner(prov_source(provider), prov_data, delayed=provision_time)


@pytest.mark.provider([RHEVMProvider],
                      required_fields=[['provisioning', 'template'],
                                       ['provisioning', 'host'],
                                       ['provisioning', 'datastore']])
@pytest.mark.parametrize('vnic_profile', ['<No Profile>', '<Use template nics>'],
                         ids=['no_profile', 'use_template_nics'])
def test_provisioning_vnic_profiles(provisioner, provider, prov_data, vm_name, vnic_profile):
    """ Tests provision VM with other than specific vnic profile selected - <No Profile>
        and <Use template nics>.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set vlan
          to values <No Profile>/<Use template nics>
        * Submit the provisioning request, it should provision the vm successfully.
        * Check NIC configuration of provisioned VM

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['network'] = {'vlan': vnic_profile}

    vm = provisioner(prov_source(provider), prov_data)

    wait_for(
        lambda: vm.exists_on_provider,
        num_sec=300, delay=5
    )

    if vnic_profile == '<No Profile>':
        # Check the VM vNIC
        nics = vm.mgmt.get_nics()
        assert nics, 'The VM should have a NIC attached.'

        # Check the vNIC network profile
        profile = nics[0].vnic_profile
        assert not profile, 'The vNIC profile should be empty.'


@pytest.mark.provider([RHEVMProvider],
                      required_fields=[['provisioning', 'template_2_nics']])
@pytest.mark.meta(blockers=[BZ(1625139, forced_streams=['5.10', 'upstream'])])
def test_provision_vm_with_2_nics(provisioner, provisioning, prov_data, vm_name):
    """ Tests provision VM from a template configured with 2 NICs.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME, template with 2 NICs

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, select template with 2 NICs.
        * Submit the provisioning request, it should provision the vm successfully.
        * Check NIC configuration of provisioned VM - it should have 2 NICs attached.

    Bugzilla:
        1625139

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
        testSteps:
            1. Open the provisioning dialog.
            2. Apart from the usual provisioning settings, select template with 2 NICs.
            3. Submit the provisioning request, it should provision the vm successfully.
            4. Check NIC configuration of provisioned VM - it should have 2 NICs attached.
    """
    template_name = provisioning.get('template_2_nics', None)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['network']['vlan'] = '<Use template nics>'

    vm = provisioner(template_name, prov_data)

    nics = vm.mgmt.get_nics()
    assert len(nics) == 2, 'The VM should have 2 NICs attached.'


@pytest.mark.provider([VMwareProvider])
def test_vmware_default_placement(provisioner, prov_data, provider, setup_provider, vm_name):
    """ Tests whether vm placed in Datacenter root after the provisioning.

    Prerequisites:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set "Choose automatically"
        * Submit the provisioning request and wait for it to finish.
        * The VM should be placed in the Datacenter root folder (that's two levels up in API).
    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['environment'] = {'automatic_placement': True}

    vm = provisioner(prov_source(provider), prov_data)

    wait_for(
        lambda: vm.exists_on_provider,
        num_sec=240, delay=5,
        message=f"VM {vm_name} exists on provider."
    )
    assert 'Datacenter' == provider.mgmt.get_vm(vm_name).raw.parent.parent.name, (
        'The new vm is not placed in the Datacenter root directory!')


@pytest.mark.provider([RHEVMProvider], required_fields=[['provisioning', 'template_false_sparse']])
@pytest.mark.meta(automates=[1726590], blockers=[BZ(1726590, forced_streams=["5.10"])])
def test_linked_clone_default(provisioner, provisioning, provider, prov_data, vm_name):
    """ Tests provision VM from a template with the selected "Linked Clone" option.
    The template must have preallocated disks (at least one) for this test.

    Required_fields is set to [['cap_and_util', 'capandu_vm']] because template for this VM has
    a preallocated disk for sure.

    Bugzilla:
        1726590

    Metadata:
        test_flag: provision

    Polarion:
        assignee: anikifor
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    template_name = provider.data['provisioning']['template_false_sparse']
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['catalog']['linked_clone'] = True
    # should be automatic but due to limited storage on rhv sometimes it may fail
    prov_data['environment'] = {'automatic_placement': True}

    provisioner(template_name, prov_data)
