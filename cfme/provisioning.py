# -*- coding: utf-8 -*-
from cfme.fixtures import pytest_selenium as sel
from cfme.services import requests
from cfme import web_ui as ui
from cfme.web_ui import fill, flash, form_buttons, tabstrip, toolbar
from collections import OrderedDict
from utils import version
from utils.log import logger
from utils.wait import wait_for

from cfme.web_ui.menu import nav
import cfme.infrastructure.virtual_machines  # To ensure the infra_vm_and_templates is available
import cfme.cloud.instance
assert cfme  # To prevent flake8 compalining


instances_by_provider_tree = ui.Tree("ul.dynatree-container")
submit_button = form_buttons.FormButton("Submit")

template_select_form = ui.Form(
    fields=[
        ('template_table', ui.Table('//div[@id="pre_prov_div"]/fieldset/table')),
        ('continue_button', submit_button),
        ('cancel_button', form_buttons.cancel)
    ]
)


def select_security_group(sg):
    """Workaround for select box that is immediately replaced by the same
       select box no matter what selenium clicks on (but works fine
       manually).  For now only selects one item even though it's a
       multiselect.

    """
    val = sel.get_attribute("//select[@id='environment__security_groups']/option[.='%s']" %
                            sg, 'value')
    sel.browser().execute_script(
        "$j('#environment__security_groups').val('%s');"
        "$j.ajax({type: 'POST', url: '/miq_request/prov_field_changed/new',"
        " data: {'environment__security_groups':'%s'}})" % (val, val))
    sel.wait_for_ajax()
    sel.sleep(1)

provisioning_form = tabstrip.TabStripForm(
    fields=[
        ('submit_button', form_buttons.FormButton("Submit")),
        ('cancel_button', form_buttons.cancel),
        ('host_submit_button', form_buttons.host_provision_submit),
        ('host_cancel_button', form_buttons.host_provision_cancel)
    ],
    tab_fields=OrderedDict([

        ('Request', [
            ('email', '//input[@name="requester__owner_email"]'),
            ('first_name', 'input#requester__owner_first_name'),
            ('last_name', 'input#requester__owner_last_name'),
            ('notes', 'textarea#requester__request_notes'),
            ('manager_name', 'input#requester__owner_manager')
        ]),

        ('Purpose', [
            ('apply_tags', ui.CheckboxTree({
                version.LOWEST: '//div[@id="all_tags_treebox"]//table',
                "5.3": '//div[@id="all_tags_treebox"]//ul',
            }))
        ]),

        ('Catalog', [
            # Cloud
            ('num_instances', ui.Select('select#service__number_of_vms')),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', 'textarea#service__vm_description'),

            # Infra
            ('vm_filter', ui.Select('select#service__vm_filter#')),
            ('num_vms', ui.Select('select#service__number_of_vms')),
            ('vm_name', '//input[@name="service__vm_name"]'),
            ('vm_description', 'textarea#service__vm_description'),
            ('catalog_name', ui.Table('//div[@id="prov_vm_div"]/table')),
            ('provision_type', ui.Select('select#service__provision_type')),
            ('linked_clone', 'input#service__linked_clone'),
            ('pxe_server', ui.Select('select#service__pxe_server_id')),
            ('pxe_image', ui.Table('//div[@id="prov_pxe_img_div"]/table')),
            ('iso_file', ui.Table('//div[@id="prov_iso_img_div"]/table'))
        ]),

        ('Environment', [
            ('automatic_placement', 'input#environment__placement_auto'),

            # Cloud
            ('availability_zone', ui.Select('select#environment__placement_availability_zone')),
            ('virtual_private_cloud', ui.Select('select#environment__cloud_network')),
            ('cloud_subnet', ui.Select('select#environment__cloud_subnet')),
            ('cloud_network', ui.Select('select#environment__cloud_network')),
            ('security_groups', select_security_group),
            ('public_ip_address', ui.Select('select#environment__floating_ip_address')),

            # Infra
            ('provider_name', ui.Select('select#environment__placement_ems_name')),
            ('datacenter', ui.Select('select#environment__placement_dc_name')),
            ('cluster', ui.Select('select#environment__placement_cluster_name')),
            ('resource_pool', ui.Select('select#environment__placement_rp_name')),
            ('folder', ui.Select('select#environment__placement_folder_name')),
            ('host_filter', ui.Select('select#environment__host_filter')),
            ('host_name', ui.Table('//div[@id="prov_host_div"]/table')),
            ('datastore_create', '#environment__new_datastore_create'),
            ('datastore_filter', ui.Select('select#environment__ds_filter')),
            ('datastore_name', ui.Table('//div[@id="prov_ds_div"]/table')),
        ]),
        ('Hardware', [
            ('num_sockets', ui.Select('select#hardware__number_of_sockets')),
            ('cores_per_socket', ui.Select('select#hardware__cores_per_socket')),
            ('memory', ui.Select('select#hardware__vm_memory')),
            ('disk_format', ui.Radio('hardware__disk_format')),
            ('vm_limit_cpu', 'input#hardware__cpu_limit'),
            ('vm_limit_memory', 'input#hardware__memory_limit'),
            ('vm_reserve_cpu', 'input#hardware__cpu_reserve'),
            ('vm_reserve_memory', 'input#hardware__memory_reserve'),
        ]),

        # Infra
        ('Network', [
            ('vlan', ui.Select('select#network__vlan')),
        ]),

        # Cloud
        ('Properties', [
            ('instance_type', ui.Select('select#hardware__instance_type')),
            ('guest_keypair', ui.Select('select#hardware__guest_access_key_pair')),
            ('hardware_monitoring', ui.Select('select#hardware__monitoring')),
        ]),

        ('Customize', [
            # Common
            ('dns_servers', 'input#customize__dns_servers'),
            ('dns_suffixes', 'input#customize__dns_suffixes'),

            # Cloud
            ('specification', ui.Select('select#customize__sysprep_enabled')),
            ('specification_name', ui.Table('//div[@id="prov_vc_div"]/table')),
            ('computer_name', 'input#customize__linux_host_name'),
            ('domain_name', 'input#customize__linux_domain_name'),

            # Infra
            ('customize_type', ui.Select('select#customize__sysprep_enabled')),
            ('specification_name', ui.Table('//div[@id="prov_vc_div"]/table')),
            ('linux_host_name', 'input#customize__linux_host_name'),
            ('linux_domain_name', 'input#customize__linux_domain_name'),
            ('prov_host_name', 'input#customize__hostname'),
            ('ip_address', 'input#customize__ip_addr'),
            ('subnet_mask', 'input#customize__subnet_mask'),
            ('gateway', 'input#customize__gateway'),
            ('custom_template', ui.Table('//div[@id="prov_template_div"]/table')),
            ('root_password', 'input#customize__root_password'),
            ('vm_host_name', 'input#customize__hostname'),
        ]),
        ('Schedule', [
            # Common
            ('schedule_type', ui.Radio('schedule__schedule_type')),
            ('provision_date', ui.Calendar('miq_date_1')),
            ('provision_start_hour', ui.Select('select#start_hour')),
            ('provision_start_min', ui.Select('select#start_min')),
            ('power_on', 'input#schedule__vm_auto_start'),
            ('retirement', ui.Select('select#schedule__retirement')),
            ('retirement_warning', ui.Select('select#schedule__retirement_warn')),

            # Infra
            ('stateless', 'input#schedule__stateless'),
        ])
    ])
)


def generate_nav_function(tb_item):
    def f(context):
        toolbar.select('Lifecycle', tb_item)
        provider = context['provider']
        template_name = context['template_name']

        template = template_select_form.template_table.find_row_by_cells({
            'Name': template_name,
            'Provider': provider.name
        })
        if template:
            sel.click(template)
            sel.click(template_select_form.continue_button)
        else:
            # Better exception?
            raise ValueError('Navigation failed: Unable to find template "%s" for provider "%s"' %
                (template_name, provider.key))
    return f

nav.add_branch('infra_vm_and_templates', {
    'infrastructure_provision_vms': generate_nav_function("Provision VMs"),
})

nav.add_branch('clouds_instances_by_provider', {
    'clouds_provision_instances': generate_nav_function("Provision Instances"),
})


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM {} on provider {}'.format(vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name)
    except Exception as e:
        logger.warning('Failed to clean up VM {} on provider {}: {}'.format(vm_name,
                                                                            provider_key, str(e)))


def do_vm_provisioning(template_name, provider_crud, vm_name, provisioning_data, request,
                       provider_mgmt, provider_key, smtp_test, num_sec=1500):
    # generate_tests makes sure these have values
    sel.force_navigate('infrastructure_provision_vms', context={
        'provider': provider_crud,
        'template_name': template_name,
    })

    note = ('template %s to vm %s on provider %s' %
        (template_name, vm_name, provider_crud.key))
    provisioning_data.update({
        'email': 'template_provisioner@example.com',
        'first_name': 'Template',
        'last_name': 'Provisioner',
        'notes': note,
    })

    fill(provisioning_form, provisioning_data,
         action=provisioning_form.submit_button)
    flash.assert_no_errors()

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider_crud.key)
    wait_for(provider_mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for vm %s' % vm_name)
    row_description = 'Provision from [%s] to [%s]' % (template_name, vm_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
                       fail_func=requests.reload, num_sec=num_sec, delay=20)
    assert row.last_message.text == version.pick(
        {version.LOWEST: 'VM Provisioned Successfully',
         "5.3": 'Vm Provisioned Successfully', })

    # Wait for e-mails to appear
    def verify():
        return (
            len(
                smtp_test.get_emails(
                    text_like="%%Your Virtual Machine Request was approved%%"
                )
            ) > 0
            and len(
                smtp_test.get_emails(
                    subject_like="Your virtual machine request has Completed - VM:%%%s" % vm_name
                )
            ) > 0
        )

    wait_for(verify, message="email receive check", delay=5)
