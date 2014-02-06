"""Provisioning-related forms and helper classes.

"""
from collections import OrderedDict

from cfme import web_ui
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import tabstrip, toolbar
from cfme.web_ui.menu import nav


template_select_form = web_ui.Form(
    fields=[
        ('template_table', web_ui.Table('//div[@id="pre_prov_div"]/fieldset/table')),
        ('continue_button', '//img[@title="Continue"]'),
        ('cancel_button', '//img[@title="Continue"]')
    ]
)

provisioning_form = tabstrip.TabStripForm(
    fields=[
        ('submit_button', '//*[@id="form_buttons"]/li[1]/img'),
        ('cancel_button', '//*[@id="form_buttons"]/li[2]/img')
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
            ('apply_tags', web_ui.Tree('//div[@id="all_tags_treebox"]//table'))
        ]),
        ('Catalog', [
            ('num_instances', '//select[@id="service__number_of_vms"]'),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', '//textarea[@id="service__vm_description"]'),
            ('catalog_name', web_ui.Table('//div[@id="prov_vm_div"]/table')),
        ]),
        ('Environment', [
            ('automatic_placement', '//input[@id="environment__placement_auto"]'),
            ('availability_zone', '//select[@id="environment__placement_availability_zone"]'),
            ('security_groups', '//select[@id="environment__security_groups"]'),
            ('public_ip_address', '//select[@id="environment__floating_ip_address"]'),
        ]),
        ('Properties', [
            ('instance_type', '//select[@id="hardware__instance_type"]'),
            ('guest_keypair', '//select[@id="hardware__guest_access_key_pair"]'),
            ('hardware_monitoring', '//select[@id="hardware__monitoring"]'),
        ]),
        ('Customize', [
            ('specification', '//select[@id="customize__sysprep_enabled"]'),
            ('specification_name', web_ui.Table('//div[@id="prov_vc_div"]/table')),
            ('computer_name', '//input[@id="customize__linux_host_name"]'),
            ('domain_name', '//input[@id="customize__linux_domain_name"]'),
            ('dns_servers', '//input[@id="customize__dns_servers"]'),
            ('dns_suffixes', '//input[@id="customize__dns_suffixes"]'),
        ]),
        ('Schedule', [
            ('schedule_type', web_ui.Radio('schedule__schedule_type')),
            ('provision_date', web_ui.Calendar('miq_date_1')),
            ('provision_start_hour', '//select[@id="start_hour"]'),
            ('provision_start_min', '//select[@id="start_min"]'),
            ('power_on', '//input[@id="schedule__vm_auto_start"]'),
            ('retirement', '//select[@id="schedule__retirement"]'),
            ('retirement_warning', '//select[@id="schedule__retirement_warn"]'),
        ])
    ])
)


# Nav targets and helpers
def _nav_to_provision_form(context):
    toolbar.select('Lifecycle', 'Provision VMs')
    provider = context['provider']
    template_name = context['template_name']

    template = template_select_form.template_table.find_row_by_cells({
        'Name': template_name,
        'Provider': provider.name
    })
    if template:
        sel.click(template)
        sel.click(template_select_form.continue_button)
        return
    else:
        # Better exception?
        raise ValueError('Navigation failed: Unable to find template "%s" for provider "%s"' %
            (template_name, provider.name))

nav.add_branch('infrastructure_virtual_machines', {
    'infrastructure_provision_instances': _nav_to_provision_form
})
