# -*- coding: utf-8 -*-
from collections import OrderedDict

from cfme import web_ui as ui
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.virtual_machines import Vm
from cfme.services.requests import RequestCollection
from cfme.web_ui import AngularSelect, flash, form_buttons, tabstrip
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

submit_button = form_buttons.FormButton("Submit")


def select_security_group(sg):
    """TODO: Not even sure this is needed any more, but removal of it is not part of this PR"""
    sel.wait_for_ajax()
    sel.sleep(1)


# TODO remove old form once all importers have moved to widget form
provisioning_form = tabstrip.TabStripForm(
    fields=[
        ('submit_button', form_buttons.FormButton("Submit")),
        ('submit_copy_button', form_buttons.FormButton("Submit this provisioning request")),
        ('cancel_button', form_buttons.cancel),
        ('host_submit_button', form_buttons.host_provision_submit),
        ('host_cancel_button', form_buttons.host_provision_cancel)
    ],
    tab_fields=OrderedDict([

        ('Request', [
            ('email', ui.Input('requester__owner_email')),
            ('first_name', ui.Input('requester__owner_first_name')),
            ('last_name', ui.Input('requester__owner_last_name')),
            ('notes', ui.Input('requester__request_notes')),
            ('manager_name', ui.Input('requester__owner_manager'))
        ]),

        ('Purpose', [
            ('apply_tags', {
                version.LOWEST: ui.CheckboxTree('//div[@id="all_tags_treebox"]//ul'),
                '5.7': ui.BootstrapTreeview('all_tags_treebox')})
        ]),

        ('Catalog', [
            # Cloud
            ('num_instances', AngularSelect('service__number_of_vms')),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', ui.Input('service__vm_description')),

            # Infra
            ('vm_filter', AngularSelect('service__vm_filter')),
            ('num_vms', AngularSelect('service__number_of_vms')),
            ('vm_name', '//input[@name="service__vm_name"]'),
            ('vm_description', ui.Input('service__vm_description')),
            ('catalog_name', ui.Table('//div[@id="prov_vm_div"]/table')),
            ('provision_type', AngularSelect('service__provision_type')),
            ('linked_clone', ui.Input('service__linked_clone')),
            ('pxe_server', AngularSelect('service__pxe_server_id')),
            ('pxe_image', ui.Table('//div[@id="prov_pxe_img_div"]/table')),
            ('iso_file', ui.Table('//div[@id="prov_iso_img_div"]/table'))
        ]),

        ('Environment', [
            ('automatic_placement', ui.Input('environment__placement_auto')),

            # Cloud
            ('cloud_tenant', AngularSelect('environment__cloud_tenant')),
            ('availability_zone', AngularSelect('environment__placement_availability_zone')),
            ('virtual_private_cloud', AngularSelect('environment__cloud_network')),
            ('cloud_network', AngularSelect('environment__cloud_network')),
            ('cloud_subnet', AngularSelect('environment__cloud_subnet')),
            ('security_groups', AngularSelect('environment__security_groups')),
            ('resource_groups', AngularSelect('environment__resource_group')),
            ('public_ip_address', AngularSelect('environment__floating_ip_address')),



            # Infra
            ('provider_name', AngularSelect('environment__placement_ems_name')),
            ('datacenter', AngularSelect('environment__placement_dc_name')),
            ('cluster', AngularSelect('environment__placement_cluster_name')),
            ('resource_pool', AngularSelect('environment__placement_rp_name')),
            ('folder', AngularSelect('environment__placement_folder_name')),
            ('host_filter', AngularSelect('environment__host_filter')),
            ('host_name', ui.Table('//div[@id="prov_host_div"]/table')),
            ('datastore_create', '#environment__new_datastore_create'),
            ('datastore_filter', AngularSelect('environment__ds_filter')),
            ('datastore_name', ui.Table('//div[@id="prov_ds_div"]/table')),
        ]),
        ('Hardware', [
            ('num_sockets', AngularSelect('hardware__number_of_sockets')),
            ('cores_per_socket', AngularSelect('hardware__cores_per_socket')),
            ('num_cpus', AngularSelect('hardware__number_of_cpus')),
            ('memory', AngularSelect('hardware__vm_memory')),
            ('disk_format', ui.Radio('hardware__disk_format')),
            ('vm_limit_cpu', ui.Input('hardware__cpu_limit')),
            ('vm_limit_memory', ui.Input('hardware__memory_limit')),
            ('vm_reserve_cpu', ui.Input('hardware__cpu_reserve')),
            ('vm_reserve_memory', ui.Input('hardware__memory_reserve')),
        ]),

        # Infra
        ('Network', [
            ('vlan', AngularSelect('network__vlan')),
        ]),

        # Cloud
        ('Properties', [
            ('instance_type', AngularSelect('hardware__instance_type')),
            ('guest_keypair', AngularSelect('hardware__guest_access_key_pair',
                                            none={'5.4': "<None>",
                                                  version.LOWEST: "<No Choices Available>"})),
            ('hardware_monitoring', AngularSelect('hardware__monitoring')),
            ('boot_disk_size', AngularSelect('hardware__boot_disk_size')),
            # GCE
            ('is_preemtible', {version.LOWEST: None,
                              '5.7': ui.Input('hardware__is_preemptible')})
        ]),

        ('Customize', [
            # Common
            ('dns_servers', ui.Input('customize__dns_servers')),
            ('dns_suffixes', ui.Input('customize__dns_suffixes')),
            ('specification', AngularSelect('customize__sysprep_enabled')),
            ('customize_type', AngularSelect('customize__sysprep_enabled')),
            ('specification_name', ui.Table('//div[@id="prov_vc_div"]/table')),

            # Cloud
            ('computer_name', ui.Input('customize__linux_host_name')),
            ('domain_name', ui.Input('customize__linux_domain_name')),

            # Azure
            ('admin_username', ui.Input('customize__root_username')),
            ('admin_password', ui.Input('customize__root_password')),

            # Infra
            ('linux_host_name', ui.Input('customize__linux_host_name')),
            ('linux_domain_name', ui.Input('customize__linux_domain_name')),
            ('prov_host_name', ui.Input('customize__hostname')),
            ('ip_address', ui.Input('customize__ip_addr')),
            ('subnet_mask', ui.Input('customize__subnet_mask')),
            ('gateway', ui.Input('customize__gateway')),
            ('custom_template', ui.Table('//div[@id="prov_template_div"]/table')),
            ('root_password', ui.Input('customize__root_password')),
            ('vm_host_name', ui.Input('customize__hostname')),
        ]),
        ('Schedule', [
            # Common
            ('schedule_type', ui.Radio('schedule__schedule_type')),
            ('provision_date', ui.Calendar('miq_date_1')),
            ('provision_start_hour', AngularSelect('start_hour')),
            ('provision_start_min', AngularSelect('start_min')),
            ('power_on', ui.Input('schedule__vm_auto_start')),
            ('retirement', AngularSelect('schedule__retirement')),
            ('retirement_warning', AngularSelect('schedule__retirement_warn')),

            # Infra
            ('stateless', ui.Input('schedule__stateless')),
        ])
    ])
)


def do_vm_provisioning(appliance, template_name, provider, vm_name, provisioning_data, request,
                       smtp_test, num_sec=1500, wait=True):
    # generate_tests makes sure these have values
    vm = Vm(name=vm_name, provider=provider, template_name=template_name)
    note = ('template {} to vm {} on provider {}'.format(template_name, vm_name, provider.key))
    provisioning_data.update({
        'request': {
            'email': 'template_provisioner@example.com',
            'first_name': 'Template',
            'last_name': 'Provisioner',
            'notes': note}})
    view = navigate_to(vm, 'Provision')
    view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
    flash.assert_no_errors()
    if not wait:
        return

    # Provision Re important in this test
    logger.info('Waiting for cfme provision request for vm %s', vm_name)
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = RequestCollection(appliance).instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.is_succeeded(method='ui'), \
        "Provisioning failed with the message {}".format(provision_request.row.last_message.text)

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider.key)
    wait_for(provider.mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

    if smtp_test:
        # Wait for e-mails to appear
        def verify():
            approval = dict(subject_like="%%Your Virtual Machine configuration was Approved%%")
            expected_text = "Your virtual machine request has Completed - VM:%%{}".format(vm_name)
            return (
                len(smtp_test.get_emails(**approval)) > 0 and
                len(smtp_test.get_emails(subject_like=expected_text)) > 0
            )

        wait_for(verify, message="email receive check", delay=30)
