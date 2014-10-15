"""Service Catalog item for EC2 , does not provision any VM just create a
catalog item of type "Amazon

"""
import functools
import ui_navigate as nav

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui as web_ui
import cfme.web_ui.toolbar as tb
from cfme.cloud import provisioning as prov
from collections import OrderedDict
from cfme.web_ui import accordion, tabstrip, Form, Table, Select, fill, flash, form_buttons
from utils.update import Updateable
from utils import version
from utils.pretty import Pretty


tb_select = functools.partial(tb.select, "Configuration")
catalog_item_tree = web_ui.Tree({
    version.LOWEST: '//div[@id="sandt_tree_box"]//table',
    '5.3': '//div[@id="sandt_treebox"]//ul'
})

template_select_form = Form(
    fields=[
        ('template_table', Table('//div[@id="prov_vm_div"]//table[@class="style3"]')),
        ('add_button', form_buttons.add),
        ('cancel_button', form_buttons.cancel)
    ]
)

# Forms
basic_info_form = Form(
    fields=[
        ('name_text', "//input[@id='name']"),
        ('description_text', "//input[@id='description']"),
        ('display_checkbox', "//input[@id='display']"),
        ('select_catalog', Select("//select[@id='catalog_id']")),
        ('select_dialog', Select("//select[@id='dialog_id']")),
        ('edit_button', form_buttons.save)
    ])


detail_form = Form(
    fields=[
        ('long_desc', "//textarea[@id='long_description']")
    ])


request_form = tabstrip.TabStripForm(
    tab_fields=OrderedDict([
        ('Catalog', [
            ('num_instances', web_ui.Select('//select[@id="service__number_of_vms"]')),
            ('instance_name', '//input[@name="service__vm_name"]'),
            ('instance_description', '//textarea[@id="service__vm_description"]'),
            ('catalog_name', web_ui.Table('//div[@id="prov_vm_div"]/table')),
        ]),
        ('Environment', [
            ('automatic_placement', '//input[@id="environment__placement_auto"]'),
            ('availability_zone',
                web_ui.Select('//select[@id="environment__placement_availability_zone"]')),
            ('security_groups', prov.select_security_group),
            ('public_ip_address',
             web_ui.Select('//select[@id="environment__floating_ip_address"]')),
        ]),
        ('Properties', [
            ('instance_type', web_ui.Select('//select[@id="hardware__instance_type"]')),
            ('guest_keypair', web_ui.Select('//select[@id="hardware__guest_access_key_pair"]')),
            ('hardware_monitoring', web_ui.Select('//select[@id="hardware__monitoring"]')),
        ]),
        ('Customize', [
            ('specification', web_ui.Select('//select[@id="customize__sysprep_enabled"]')),
            ('specification_name', web_ui.Table('//div[@id="prov_vc_div"]/table')),
            ('computer_name', '//input[@id="customize__linux_host_name"]'),
            ('domain_name', '//input[@id="customize__linux_domain_name"]'),
            ('dns_servers', '//input[@id="customize__dns_servers"]'),
            ('dns_suffixes', '//input[@id="customize__dns_suffixes"]'),
        ]),
        ('Schedule', [
            ('schedule_type', web_ui.Radio('schedule__schedule_type')),
            ('provision_date', web_ui.Calendar('miq_date_1')),
            ('provision_start_hour', web_ui.Select('//select[@id="start_hour"]')),
            ('provision_start_min', web_ui.Select('//select[@id="start_min"]')),
            ('power_on', '//input[@id="schedule__vm_auto_start"]'),
            ('retirement', web_ui.Select('//select[@id="schedule__retirement"]')),
            ('retirement_warning', web_ui.Select('//select[@id="schedule__retirement_warn"]')),
        ])
    ])
)


def _all_catalogitems_add_new(context):
    catalog_item_tree.click_path('All Catalog Items')
    tb_select('Add a New Catalog Item')
    provider_type = context['provider_type']
    sel.select("//select[@id='st_prov_type']", provider_type)


def _all_catalogbundle_add_new(context):
    sel.click("//div[@id='sandt_tree_div']//td[.='All Catalog Items']")
    tb_select('Add a New Catalog Bundle')


nav.add_branch(
    'services_catalogs',
    {'catalog_items': [nav.partial(accordion.click, 'Catalog Items'),
        {'catalog_item_new': _all_catalogitems_add_new,
         'catalog_item': [lambda ctx: catalog_item_tree.
                          click_path('All Catalog Items',
                                     ctx['catalog'], ctx['catalog_item'].name),
                          {'catalog_item_edit': nav.partial(tb_select,
                                                            "Edit this Item")}]}]})


class Template(Pretty):
    pretty_attrs = ['name']

    def __init__(self, name):
        self.name = name


class Instance(Updateable, Pretty):
    pretty_attrs = ['name', 'item_type', 'catalog', 'vm_name', 'instance_type', 'availability_zone']

    def __init__(self, item_type=None, name=None, description=None,
                 display_in=False, catalog=None, dialog=None, vm_name=None, catalog_name=None,
                 instance_type=None, availability_zone=None, security_groups=None,
                 provider=None, provider_mgmt=None, guest_keypair=None):
        self.item_type = item_type
        self.name = name
        self.description = description
        self.display_in = display_in
        self.catalog = catalog
        self.dialog = dialog
        self.vm_name = vm_name
        self.catalog_name = catalog_name
        self.instance_type = instance_type
        self.availability_zone = availability_zone
        self.security_groups = security_groups
        self.provider = provider
        self.provider_mgmt = provider_mgmt
        self.guest_keypair = guest_keypair

    def create(self):
        sel.force_navigate('catalog_item_new', context={'provider_type': self.item_type})
        fill(basic_info_form, {'name_text': self.name,
                               'description_text': self.description,
                               'display_checkbox': self.display_in,
                               'select_catalog': self.catalog,
                               'select_dialog': self.dialog})
        tabstrip.select_tab("Request Info")
        template = template_select_form.template_table.find_row_by_cells({
            'Name': self.catalog_name,
            'Provider': self.provider
        })
        sel.click(template)
        web_ui.fill(request_form, {
            'instance_name': self.vm_name,
            'instance_type': self.instance_type,
            'guest_keypair': self.guest_keypair,
            'availability_zone': self.availability_zone,
            'security_groups': self.security_groups[0],  # not supporting multiselect now,
                                                         # just take first value
        })
        sel.click(template_select_form.add_button)
        flash.assert_success_message('Service Catalog Item "%s" was added' % self.name)
