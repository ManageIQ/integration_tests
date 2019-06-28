# -*- coding: utf-8 -*-
"""Manual VMware Provider tests"""
import os
import re
import tarfile

import fauxfactory
import pytest
from six.moves.urllib import request as url_request

from cfme import test_requirements
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger

pytestmark = [
    test_requirements.vmware,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider', 'uses_infra_providers'),
    pytest.mark.provider([VMwareProvider],
                        required_fields=[['provisioning', 'template'],
                                        ['provisioning', 'host'],
                                        ['provisioning', 'datastore'],
                                        (["cap_and_util", "capandu_vm"], "cu-24x7")],
                        scope="module")
]


@pytest.mark.tier(3)
def test_vmware_provider_filters(appliance, provider, soft_assert):
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
    esx_platforms = ['Platform / ESX 6.0', 'Platform / ESX 6.5', 'Platform / ESX 6.7']
    view = navigate_to(appliance.collections.hosts, 'All')
    all_options = view.filters.navigation.all_options
    logger.info("All options for Filters are: {} ".format(all_options))
    for esx_platform in esx_platforms:
        soft_assert(esx_platform in all_options, "ESX Platform does not exists in options")


@pytest.mark.tier(3)
@pytest.mark.long_running
@pytest.mark.ignore_stream("upstream")
@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, override=True)
def test_appliance_scsi_control_vmware(request, appliance):
    """
    Appliance cfme-vsphere-paravirtual-*.ova has SCSI controller as Para
    Virtual

    Polarion:
        assignee: kkulkarn
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/4h
    """
    try:
        url = (conf.cfme_data.basic_info.cfme_images_url.cfme_paravirtual_url_format
            .format(
                baseurl=conf.cfme_data.basic_info.cfme_images_url.baseurl,
                series=appliance.version.series(), ver=appliance.version
            )
        )
    except AttributeError:
        pytest.skip('Skipping as one of the keys might be missing in cfme_yamls.')
    logger.info("Downloading ova file for parvirtual vsphere scsi controller test from %s", url)
    filename = os.path.basename(url)

    url_request.urlretrieve(url, filename)

    @request.addfinalizer
    def _cleanup():
        if os.path.exists(filename):
            os.remove(filename)

    with tarfile.open(filename) as tar:
        desc_member = tar.getmember("desc.ovf")
        f = tar.extractfile(desc_member)
        content = f.read()
    assert content, "No content could be read from desc.ovf"
    logger.debug("Desc file contains following text:%s" % content)
    check_string = '<rasd:ResourceSubType>VirtualSCSI</rasd:ResourceSubType>'
    assert check_string in str(content), "Given OVA does not have paravirtual scsi controller"


@pytest.mark.tier(1)
def test_vmware_vds_ui_display(soft_assert, appliance, provider):
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
    try:
        host = provider.hosts.all()[0]
    except IndexError:
        pytest.skip("No hosts found")
    view = navigate_to(host, 'Networks')
    soft_assert('DSwitch' in view.network_tree.all_options, "No DSwitches on Host Network page")
    assert 'DSwitch' in [s.name for s in appliance.collections.infra_switches.all()], ('No DSwitch'
        'on networking page')


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1650441, forced_streams=['5.10', '5.11'])])
def test_vmware_reconfigure_vm_controller_type(appliance, provider):
    """
    Edit any VM which is provisioned for vSphere and select "Reconfigure this VM" option.
    In "Controller Type" column we do not see the Controller Type listed.
    Controller Type should be listed.

    Bugzilla:
        1650441

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
    vms_collections = appliance.collections.infra_vms
    vm = vms_collections.instantiate(name='cu-24x7', provider=provider)
    if not vm.exists_on_provider:
        pytest.skip("Skipping test, cu-24x7 VM does not exist")
    view = navigate_to(vm, 'Reconfigure')
    # grab the first row of the table
    row = view.disks_table[0]
    assert not row.controller_type.read() == '', "Failed, as the Controller Type Column has no text"


@pytest.mark.tier(1)
def test_vmware_vds_ui_tagging(appliance, provider, soft_assert):
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
            2.Compute > Infrastructure > Networkiong
            3.Check if host has Distributed Switch and it is displayed on this page
            4.If displayed, try to select Policy->Assign Tag to DSwitch.
        expectedResults:
            1.
            2.Networking Page opens
            3.If DSwitch exists it will be displayed on this page.
            4.You can assign tags to DSwitch.
    """
    switches_collection = appliance.collections.infra_switches
    switches = [switch for switch in switches_collection.all() if switch.name == 'DSwitch']
    assert switches, "There are no DSwitches on Networking Page"
    s = switches[0]
    s.add_tag((appliance.collections.categories.instantiate(display_name='Owner')
            .collections.tags.instantiate(display_name='Production Linux Team')))
    added_tags = [tag for tag in s.get_tags()
                if (tag.name == 'Owner') and
                (tag.display_name == 'Production Linux Team')]
    assert added_tags, "Failed to retrieve correct tags"


@pytest.mark.manual
@pytest.mark.tier(1)
def test_vmware_inaccessible_datastore():
    """
    VMware sometimes has datastores that are inaccessible, and CloudForms should indicate that.

    Bugzilla:
        1684656

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


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1689369, forced_streams=['5.10', '5.11'])])
def test_vmware_cdrom_dropdown_not_blank(appliance, provider):
    """
    Test CD/DVD Drives dropdown lists ISO files, dropdown is not blank

    Bugzilla:
        1689369

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
    datastore_collection = appliance.collections.datastores
    ds = [ds.name for ds in provider.data['datastores'] if ds.type == 'iso']
    try:
        iso_ds = datastore_collection.instantiate(name=ds[0], provider=provider)
    except IndexError:
        pytest.skip('No datastores found of type iso on provider {}'.format(provider.name))
    iso_ds.run_smartstate_analysis()
    vms_collections = appliance.collections.infra_vms
    vm = vms_collections.instantiate(name='cu-24x7', provider=provider)
    if not vm.exists_on_provider:
        pytest.skip("Skipping test, cu-24x7 VM does not exist")
    view = navigate_to(vm, 'Reconfigure')
    # Fetch the actions_column for first row in the table
    try:
        actions_column = view.cd_dvd_table[0]['Actions']
    except IndexError:
        pytest.skip("CD DVD Table is empty, has no rows.")
    # First disconnect if already connected
    assert actions_column.text == 'Connect Disconnect'
    actions_column.click()
    # Confirm disconnect
    assert actions_column.text == 'Confirm'
    actions_column.click()
    # if 'Connect' option is present, click it
    assert actions_column.text == 'Connect'
    actions_column.click()
    # Fetch the host_file_column for first row in the table
    host_file_column = view.cd_dvd_table[0]['Host File']
    assert host_file_column.widget.is_displayed  # Assert BootStrapSelect is displayed
    assert not host_file_column.widget.all_options == []
    all_isos = [opt.text for opt in host_file_column.widget.all_options if 'iso' in opt.text]
    assert all_isos, "Dropdown for isos is empty"


@pytest.mark.tier(1)
def test_vmware_inaccessible_datastore_vm_provisioning(request, appliance, provider):
    """
    VMware sometimes has datastores that are inaccessible, and CloudForms should not pick this
    during provisioning when using "Choose Automatically" as an option under environment tab.

    Bugzilla:
        1694137

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
    inaccessible_datastores = [
        datastore for datastore in provider.mgmt.list_datastore()
        if not provider.mgmt.get_datastore(datastore).summary.accessible]
    if inaccessible_datastores:
        logger.info("Found {} inaccessible_datastores".format(inaccessible_datastores))
    else:
        pytest.skip("This provider {} has no inaccessible_datastores.".format(provider.name))
    vm = appliance.collections.infra_vms.create('test-vmware-{}'.format(
        fauxfactory.gen_alphanumeric()), provider, find_in_cfme=True, wait=True,
        form_values={'environment': {'automatic_placement': True}})
    request.addfinalizer(vm.delete)
    assert vm.datastore.name not in inaccessible_datastores


@pytest.mark.tier(1)
def test_vmware_provisioned_vm_host_relationship(request, appliance, provider):
    """
    VMware VMs provisioned through cloudforms should have host relationship.

    Bugzilla:
        1657341

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
    vm = appliance.collections.infra_vms.create('test-vmware-{}'
        .format(fauxfactory.gen_alphanumeric()),
        provider, find_in_cfme=True, wait=True,
        form_values={'environment': {'automatic_placement': True}})
    request.addfinalizer(vm.delete)
    # assert if Host property is set for VM.
    assert isinstance(vm.host, Host)
    view = navigate_to(vm, "Details")
    assert view.entities.summary('Relationships').get_text_of('Host') == vm.host.name


@pytest.mark.tier(1)
def test_esxi_reboot_not_orphan_vms(appliance, provider):
    """
    By mimicking ESXi reboot effect on VMs in CFME, make sure they are not getting marked orphaned.

    Bugzilla:
        1695008

    Polarion:
        assignee: kkulkarn
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/2h
        testtype: integration
        testSteps:
            1.Add VMware provider to CFME
            2.SSH to CFME appliance and perform following steps in rails console
                '''
                ems = ManageIQ::Providers::Vmware::InfraManager.find_by(:name => "name of your vc")
                vm = ems.vms.last # Or do vms[index] and find a vm to work with
                puts "VM_ID [#{vm.id}],name [#{vm.name}],uid[#{vm.uid_ems}]"
                vm.update_attributes(:uid_ems => SecureRandom.uuid)
                '''
            3.Refresh the provider
        expectedResults:
            1.Provider added successfully and is refreshed
            2.VM's uid_ems is modified
            3.After a full refresh, VM is still active and usable in cfme, not archived/orphaned.
    """
    command = "'ems=ManageIQ::Providers::Vmware::InfraManager.find_by(:name =>\"" + provider.name + "\");\
                vm = ems.vms.last;\
                puts \"VM_ID=#{vm.id} name=[#{vm.name}] uid=#{vm.uid_ems}\";\
                vm.update_attributes(:uid_ems => SecureRandom.uuid);\
                puts \"VM_ID=#{vm.id} name=[#{vm.name}] uid=#{vm.uid_ems}\"'"
    result = appliance.ssh_client.run_rails_command(command)
    logger.info("Output of Rails command was {}".format(result.output))
    provider.refresh_provider_relationships()
    assert result.success, "SSH Command result was unsuccessful: {}".format(result)
    if not result.output:
        vm_name = re.findall(r"\[.+\]", result.output)[0].split('[')[1].split(']')[0]
        vm = appliance.collections.infra_vms.instantiate(name=vm_name, provider=provider)
        view = vm.load_details(from_any_provider=True)
        power_state = view.entities.summary('Power Management').get_text_of('Power State')
        assert not power_state == 'orphaned'
        assert not power_state == 'archived'
