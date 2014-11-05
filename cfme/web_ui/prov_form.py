from cfme.fixtures import pytest_selenium as sel
from cfme import web_ui as ui
from cfme.web_ui import form_buttons, tabstrip
from collections import OrderedDict
from utils import version

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
            ('first_name', '//input[@id="requester__owner_first_name"]'),
            ('last_name', '//input[@id="requester__owner_last_name"]'),
            ('notes', '//textarea[@id="requester__request_notes"]'),
            ('manager_name', '//input[@id="requester__owner_manager"]')
        ]),

        ('Purpose', [
            ('apply_tags', {
                version.LOWEST: ui.CheckboxTree('//div[@id="all_tags_treebox"]//table'),
                "5.3": ui.CheckboxTree('//div[@id="all_tags_treebox"]//ul')
            })
        ]),

        ('Catalog', [
            # Cloud
            ('num_instances', ui.Select('//select[@id="service__number_of_vms"]')),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', '//textarea[@id="service__vm_description"]'),

            # Infra
            ('vm_filter', ui.Select('//select[@id="service__vm_filter"]')),
            ('num_vms', ui.Select('//select[@id="service__number_of_vms"]')),
            ('vm_name', '//input[@name="service__vm_name"]'),
            ('vm_description', '//textarea[@id="service__vm_description"]'),
            ('catalog_name', ui.Table('//div[@id="prov_vm_div"]/table')),
            ('provision_type', ui.Select('//select[@id="service__provision_type"]')),
            ('linked_clone', '//input[@id="service__linked_clone"]'),
            ('pxe_server', ui.Select('//select[@id="service__pxe_server_id"]')),
            ('pxe_image', ui.Table('//div[@id="prov_pxe_img_div"]/table')),
            ('iso_file', ui.Table('//div[@id="prov_iso_img_div"]/table'))
        ]),

        ('Environment', [
            ('automatic_placement', '//input[@id="environment__placement_auto"]'),

            # Cloud
            ('availability_zone',
                ui.Select('//select[@id="environment__placement_availability_zone"]')),
            ('virtual_private_cloud', ui.Select('//select[@id="environment__cloud_network"]')),
            ('cloud_subnet', ui.Select('//select[@id="environment__cloud_subnet"]')),
            ('cloud_network', ui.Select('//select[@id="environment__cloud_network"]')),
            ('security_groups', select_security_group),
            ('public_ip_address', ui.Select('//select[@id="environment__floating_ip_address"]')),

            # Infra
            ('provider_name', ui.Select('//select[@id="environment__placement_ems_name"]')),
            ('datacenter', ui.Select('//select[@id="environment__placement_dc_name"]')),
            ('cluster', ui.Select('//select[@id="environment__placement_cluster_name"]')),
            ('resource_pool', ui.Select('//select[@id="environment__placement_rp_name"]')),
            ('folder', ui.Select('//select[@id="environment__placement_folder_name"]')),
            ('host_filter', ui.Select('//select[@id="environment__host_filter"]')),
            ('host_name', ui.Table('//div[@id="prov_host_div"]/table')),
            ('datastore_create', '//*[@id="environment__new_datastore_create"]'),
            ('datastore_filter', ui.Select('//select[@id="environment__ds_filter"]')),
            ('datastore_name', ui.Table('//div[@id="prov_ds_div"]/table')),
        ]),
        ('Hardware', [
            ('num_sockets', ui.Select('//select[@id="hardware__number_of_sockets"]')),
            ('cores_per_socket', ui.Select('//select[@id="hardware__cores_per_socket"]')),
            ('memory', ui.Select('//select[@id="hardware__vm_memory"]')),
            ('disk_format', ui.Radio('hardware__disk_format')),
            ('vm_limit_cpu', '//input[@id="hardware__cpu_limit"]'),
            ('vm_limit_memory', '//input[@id="hardware__memory_limit"]'),
            ('vm_reserve_cpu', '//input[@id="hardware__cpu_reserve"]'),
            ('vm_reserve_memory', '//input[@id="hardware__memory_reserve"]'),
        ]),

        # Infra
        ('Network', [
            ('vlan', ui.Select('//select[@id="network__vlan"]')),
        ]),

        # Cloud
        ('Properties', [
            ('instance_type', ui.Select('//select[@id="hardware__instance_type"]')),
            ('guest_keypair', ui.Select('//select[@id="hardware__guest_access_key_pair"]')),
            ('hardware_monitoring', ui.Select('//select[@id="hardware__monitoring"]')),
        ]),

        ('Customize', [
            # Common
            ('dns_servers', '//input[@id="customize__dns_servers"]'),
            ('dns_suffixes', '//input[@id="customize__dns_suffixes"]'),

            # Cloud
            ('specification', ui.Select('//select[@id="customize__sysprep_enabled"]')),
            ('specification_name', ui.Table('//div[@id="prov_vc_div"]/table')),
            ('computer_name', '//input[@id="customize__linux_host_name"]'),
            ('domain_name', '//input[@id="customize__linux_domain_name"]'),

            # Infra
            ('customize_type', ui.Select('//select[@id="customize__sysprep_enabled"]')),
            ('specification_name', ui.Table('//div[@id="prov_vc_div"]/table')),
            ('linux_host_name', '//input[@id="customize__linux_host_name"]'),
            ('linux_domain_name', '//input[@id="customize__linux_domain_name"]'),
            ('prov_host_name', '//input[@id="customize__hostname"]'),
            ('ip_address', '//input[@id="customize__ip_addr"]'),
            ('subnet_mask', '//input[@id="customize__subnet_mask"]'),
            ('gateway', '//input[@id="customize__gateway"]'),
            ('custom_template', ui.Table('//div[@id="prov_template_div"]/table')),
            ('root_password', '//input[@id="customize__root_password"]'),
            ('vm_host_name', '//input[@id="customize__hostname"]'),
        ]),
        ('Schedule', [
            # Common
            ('schedule_type', ui.Radio('schedule__schedule_type')),
            ('provision_date', ui.Calendar('miq_date_1')),
            ('provision_start_hour', ui.Select('//select[@id="start_hour"]')),
            ('provision_start_min', ui.Select('//select[@id="start_min"]')),
            ('power_on', '//input[@id="schedule__vm_auto_start"]'),
            ('retirement', ui.Select('//select[@id="schedule__retirement"]')),
            ('retirement_warning', ui.Select('//select[@id="schedule__retirement_warn"]')),

            # Infra
            ('stateless', '//input[@id="schedule__stateless"]'),
        ])
    ])
)
