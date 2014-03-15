"""Provisioning-related forms and helper classes.

"""
from collections import OrderedDict

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Calendar, Form, Radio, Select, Table, Tree, tabstrip, toolbar
from cfme.web_ui.menu import nav


template_select_form = Form(
    fields=[
        ('template_table', Table('//div[@id="pre_prov_div"]/fieldset/table')),
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
            ('apply_tags', Tree('//div[@id="all_tags_treebox"]//table'))
        ]),
        ('Catalog', [
            ('num_instances', Select('//select[@id="service__number_of_vms"]')),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', '//textarea[@id="service__vm_description"]'),
            ('catalog_name', Table('//div[@id="prov_vm_div"]/table')),
        ]),
        ('Environment', [
            ('automatic_placement', '//input[@id="environment__placement_auto"]'),
            ('availability_zone',
                Select('//select[@id="environment__placement_availability_zone"]')),
            ('security_groups', Select('//select[@id="environment__security_groups"]')),
            ('public_ip_address', Select('//select[@id="environment__floating_ip_address"]')),
        ]),
        ('Properties', [
            ('instance_type', Select('//select[@id="hardware__instance_type"]')),
            ('guest_keypair', Select('//select[@id="hardware__guest_access_key_pair"]')),
            ('hardware_monitoring', Select('//select[@id="hardware__monitoring"]')),
        ]),
        ('Customize', [
            ('specification', Select('//select[@id="customize__sysprep_enabled"]')),
            ('specification_name', Table('//div[@id="prov_vc_div"]/table')),
            ('computer_name', '//input[@id="customize__linux_host_name"]'),
            ('domain_name', '//input[@id="customize__linux_domain_name"]'),
            ('dns_servers', '//input[@id="customize__dns_servers"]'),
            ('dns_suffixes', '//input[@id="customize__dns_suffixes"]'),
        ]),
        ('Schedule', [
            ('schedule_type', Radio('schedule__schedule_type')),
            ('provision_date', Calendar('miq_date_1')),
            ('provision_start_hour', Select('//select[@id="start_hour"]')),
            ('provision_start_min', Select('//select[@id="start_min"]')),
            ('power_on', '//input[@id="schedule__vm_auto_start"]'),
            ('retirement', Select('//select[@id="schedule__retirement"]')),
            ('retirement_warning', Select('//select[@id="schedule__retirement_warn"]')),
        ])
    ])
)


# Nav targets and helpers
def _nav_to_provision_form(context):
    toolbar.select('Lifecycle', 'Provision Instances')
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

nav.add_branch('clouds_instances', {
    'clouds_provision_instances': _nav_to_provision_form
})
