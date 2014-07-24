"""Provisioning-related forms and domain classes.

"""
from cfme.fixtures import pytest_selenium as sel
from cfme import web_ui as ui
from cfme.web_ui import form_buttons, tabstrip, toolbar
from cfme.web_ui.menu import nav
from collections import OrderedDict

submit_button = form_buttons.FormButton("Submit")

template_select_form = ui.Form(
    fields=[
        ('template_table', ui.Table('//div[@id="pre_prov_div"]/fieldset/table')),
        ('continue_button', submit_button),
        ('cancel_button', form_buttons.cancel)
    ]
)


def select_security_group(sg):
    '''Workaround for select box that is immediately replaced by the same
       select box no matter what selenium clicks on (but works fine
       manually).  For now only selects one item even though it's a
       multiselect.

    '''
    val = sel.get_attribute("//select[@id='environment__security_groups']/option[.='%s']" %
                            sg, 'value')
    sel.browser().execute_script(
        "$j('#environment__security_groups').val('%s');"
        "$j.ajax({type: 'POST', url: '/miq_request/prov_field_changed/new',"
        " data: {'environment__security_groups':'%s'}})" % (val, val))
    sel.wait_for_ajax()
    sel.sleep(1)

instances_by_provider_tree = ui.Tree("//ul[@class='dynatree-container']")

provisioning_form = tabstrip.TabStripForm(
    fields=[
        ('submit_button', submit_button),
        ('cancel_button', form_buttons.cancel)
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
            ('apply_tags', ui.Tree('//div[@id="all_tags_treebox"]//table'))
        ]),
        ('Catalog', [
            ('num_instances', ui.Select('//select[@id="service__number_of_vms"]')),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', '//textarea[@id="service__vm_description"]'),
            ('catalog_name', ui.Table('//div[@id="prov_vm_div"]/table')),
        ]),
        ('Environment', [
            ('automatic_placement', '//input[@id="environment__placement_auto"]'),
            ('availability_zone',
                ui.Select('//select[@id="environment__placement_availability_zone"]')),
            ('virtual_private_cloud', ui.Select('//select[@id="environment__cloud_network"]')),
            ('cloud_subnet', ui.Select('//select[@id="environment__cloud_subnet"]')),
            ('cloud_network', ui.Select('//select[@id="environment__cloud_network"]')),
            ('security_groups', select_security_group),
            ('public_ip_address', ui.Select('//select[@id="environment__floating_ip_address"]'))
        ]),
        ('Properties', [
            ('instance_type', ui.Select('//select[@id="hardware__instance_type"]')),
            ('guest_keypair', ui.Select('//select[@id="hardware__guest_access_key_pair"]')),
            ('hardware_monitoring', ui.Select('//select[@id="hardware__monitoring"]')),
        ]),
        ('Customize', [
            ('specification', ui.Select('//select[@id="customize__sysprep_enabled"]')),
            ('specification_name', ui.Table('//div[@id="prov_vc_div"]/table')),
            ('computer_name', '//input[@id="customize__linux_host_name"]'),
            ('domain_name', '//input[@id="customize__linux_domain_name"]'),
            ('dns_servers', '//input[@id="customize__dns_servers"]'),
            ('dns_suffixes', '//input[@id="customize__dns_suffixes"]'),
        ]),
        ('Schedule', [
            ('schedule_type', ui.Radio('schedule__schedule_type')),
            ('provision_date', ui.Calendar('miq_date_1')),
            ('provision_start_hour', ui.Select('//select[@id="start_hour"]')),
            ('provision_start_min', ui.Select('//select[@id="start_min"]')),
            ('power_on', '//input[@id="schedule__vm_auto_start"]'),
            ('retirement', ui.Select('//select[@id="schedule__retirement"]')),
            ('retirement_warning', ui.Select('//select[@id="schedule__retirement_warn"]')),
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
    else:
        # Better exception?
        raise ValueError('Navigation failed: Unable to find template "%s" for provider "%s"' %
            (template_name, provider.name))

nav.add_branch('clouds_instances', {
    'clouds_provision_instances': _nav_to_provision_form
})
