# -*- coding: utf-8 -*-
from functools import partial
from collections import OrderedDict
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, Radio, Select, Table, accordion, fill,\
    flash, form_buttons, menu, tabstrip, DHTMLSelect
from cfme.web_ui import toolbar as tb
from utils.update import Updateable
from utils.pretty import Pretty

cfg_btn = partial(tb.select, "Configuration")
accordion_tree = partial(accordion.tree, "Catalog Items")
policy_btn = partial(tb.select, "Policy")

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

edit_tags_form = Form(
    fields=[
        ("select_value", Select("select#tag_add"))
    ])

detail_form = Form(
    fields=[
        ('long_desc', "//textarea[@id='long_description']")
    ])

request_form = tabstrip.TabStripForm(
    tab_fields=OrderedDict([
        ('Catalog', [
            ('vm_filter', Select('//select[@id="service__vm_filter"]')),
            ('catalog_name', Table('//div[@id="prov_vm_div"]/table')),
            ('vm_name', '//input[@name="service__vm_name"]'),
            ('provision_type', Select('//select[@id="service__provision_type"]')),
            ('linked_clone', '//input[@id="service__linked_clone"]'),
            ('pxe_server', Select('//select[@id="service__pxe_server_id"]')),
            ('pxe_image', Table('//div[@id="prov_pxe_img_div"]/table')),
            ('iso_file', Table('//div[@id="prov_iso_img_div"]/table')),
        ]),
        ('Environment', [
            ('automatic_placement', '//input[@id="environment__placement_auto"]'),
            ('datacenter', Select('//select[@id="environment__placement_dc_name"]')),
            ('cluster', Select('//select[@id="environment__placement_cluster_name"]')),
            ('resource_pool', Select('//select[@id="environment__placement_rp_name"]')),
            ('folder', Select('//select[@id="environment__placement_folder_name"]')),
            ('host_filter', Select('//select[@id="environment__host_filter"]')),
            ('host_name', Table('//div[@id="prov_host_div"]/table')),
            ('datastore_create', '//*[@id="environment__new_datastore_create"]'),
            ('datastore_filter', Select('//select[@id="environment__ds_filter"]')),
            ('datastore_name', Table('//div[@id="prov_ds_div"]/table')),
        ]),
        ('Hardware', [
            ('num_sockets', Select('//select[@id="hardware__number_of_sockets"]')),
            ('cores_per_socket', Select('//select[@id="hardware__cores_per_socket"]')),
            ('memory', Select('//select[@id="hardware__vm_memory"]')),
            ('disk_format', Radio('hardware__disk_format')),
            ('vm_limit_cpu', '//input[@id="hardware__cpu_limit"]'),
            ('vm_limit_memory', '//input[@id="hardware__memory_limit"]'),
            ('vm_reserve_cpu', '//input[@id="hardware__cpu_reserve"]'),
            ('vm_reserve_memory', '//input[@id="hardware__memory_reserve"]'),
        ]),
        ('Network', [
            ('vlan', Select('//select[@id="network__vlan"]')),
        ]),
        ('Customize', [
            ('customize_type', Select('//select[@id="customize__sysprep_enabled"]')),
            ('specification_name', Table('//div[@id="prov_vc_div"]/table')),
            ('linux_host_name', '//input[@id="customize__linux_host_name"]'),
            ('linux_domain_name', '//input[@id="customize__linux_domain_name"]'),
            ('dns_servers', '//input[@id="customize__dns_servers"]'),
            ('dns_suffixes', '//input[@id="customize__dns_suffixes"]'),
            ('custom_template', Table('//div[@id="prov_template_div"]/table')),
            ('root_password', '//input[@id="customize__root_password"]'),
            ('vm_host_name', '//input[@id="customize__hostname"]'),
        ]),
        ('Schedule', [
            ('power_on_vm', "//input[@id='schedule__vm_auto_start']"),
            ('retirement', Select('//select[@id="schedule__retirement"]')),
            ('retirement_warning', Select('//select[@id="schedule__retirement_warn"]')),
        ])
    ])
)

resources_form = Form(
    fields=[
        ('choose_resource', Select("//select[@id='resource_id']")),
        ('add_button', form_buttons.add),
        ('save_button', form_buttons.save)
    ])

button_group_form = Form(
    fields=[
        ('btn_group_text', "//input[@id='name']"),
        ('btn_group_hvr_text', "//input[@id='description']"),
        ('add_button', form_buttons.add)
    ])

button_form = Form(
    fields=[
        ('btn_text', "//input[@id='name']"),
        ('btn_hvr_text', "//input[@id='description']"),
        ('select_dialog', Select("//select[@id='dialog_id']")),
        ('system_process', Select("//select[@id='instance_name']")),
        ('request', "//input[@id='object_request']"),
        ('add_button', form_buttons.add)
    ])


def _all_catalogitems_add_new(context):
    accordion_tree('All Catalog Items')
    cfg_btn('Add a New Catalog Item')
    provider_type = context['provider_type']
    sel.select("//select[@id='st_prov_type']", provider_type)


def _all_catalogbundle_add_new(context):
    accordion_tree('All Catalog Items')
    cfg_btn('Add a New Catalog Bundle')


menu.nav.add_branch(
    'services_catalogs',
    {
        'catalog_items':
        [
            lambda _: accordion.click('Catalog Items'),
            {
                'catalog_item_new': _all_catalogitems_add_new,
                'catalog_item':
                [
                    lambda ctx: accordion_tree(
                        'All Catalog Items', ctx['catalog'], ctx['catalog_item'].name),
                    {
                        'catalog_item_edit': lambda _: cfg_btn("Edit this Item")
                    }
                ]
            }
        ],
        'catalog_bundle':
        [
            lambda _: accordion.click('Catalog Items'),
            {
                'catalog_bundle_new': _all_catalogbundle_add_new,
                'catalog_bundle':
                [
                    lambda ctx: accordion_tree(
                        'All Catalog Items', ctx['catalog'], ctx['catalog_bundle'].name),
                    {
                        'catalog_bundle_edit': lambda _: cfg_btn("Edit this Item")
                    }
                ]
            }
        ]
    }
)


class CatalogItem(Updateable, Pretty):
    pretty_attrs = ['name', 'item_type', 'catalog', 'catalog_name', 'provider']

    def __init__(self, item_type=None, name=None, description=None,
                 display_in=False, catalog=None, dialog=None,
                 catalog_name=None, provider=None, prov_data=None):
        self.item_type = item_type
        self.name = name
        self.description = description
        self.display_in = display_in
        self.catalog = catalog
        self.dialog = dialog
        self.catalog_name = catalog_name
        self.provider = provider
        self.provisioning_data = prov_data

    def create(self):
        sel.force_navigate('catalog_item_new',
                           context={'provider_type': self.item_type})
        fill(basic_info_form, {'name_text': self.name,
                               'description_text': self.description,
                               'display_checkbox': self.display_in,
                               'select_catalog': self.catalog,
                               'select_dialog': self.dialog})
        if(self.catalog_name is not None):
            tabstrip.select_tab("Request Info")
            template = template_select_form.template_table.find_row_by_cells({
                'Name': self.catalog_name,
                'Provider': self.provider
            })
            sel.click(template)
            request_form.fill(self.provisioning_data)
        sel.click(template_select_form.add_button)

    def update(self, updates):
        sel.force_navigate('catalog_item_edit',
                           context={'catalog': self.catalog,
                                    'catalog_item': self})
        fill(basic_info_form, {'name_text': updates.get('name', None),
                               'description_text':
                               updates.get('description', None)},
             action=basic_info_form.edit_button)
        flash.assert_success_message('Service Catalog Item "%s" was saved' %
                                     self.name)

    def delete(self):
        sel.force_navigate('catalog_item', context={'catalog': self.catalog,
                                                    'catalog_item': self})
        cfg_btn("Remove Item from the VMDB", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('The selected Catalog Item was deleted')

    def add_button_group(self):
        sel.force_navigate('catalog_item', context={'catalog': self.catalog,
                                                    'catalog_item': self})
        cfg_btn("Add a new Button Group", invokes_alert=True)
        sel.wait_for_element(button_group_form.btn_group_text)
        fill(button_group_form, {'btn_group_text': "group_text",
                                 'btn_group_hvr_text': "descr"})
        select = DHTMLSelect("div#button_div")
        select.select_by_value(1)
        sel.click(button_group_form.add_button)
        flash.assert_success_message('Buttons Group "descr" was added')

    def add_button(self):
        sel.force_navigate('catalog_item', context={'catalog': self.catalog,
                                                    'catalog_item': self})
        cfg_btn('Add a new Button', invokes_alert=True)
        sel.wait_for_element(button_form.btn_text)
        fill(button_form, {'btn_text': "btn_text",
                           'btn_hvr_text': "btn_descr"})
        select = DHTMLSelect("div#button_div")
        select.select_by_value(2)
        fill(button_form, {'select_dialog': self.dialog,
                           'system_process': "Request",
                           'request': "InspectMe"})
        sel.click(button_form.add_button)
        flash.assert_success_message('Button "btn_descr" was added')

    def edit_tags(self, value):
        sel.force_navigate('catalog_item', context={'catalog': self.catalog,
                                                    'catalog_item': self})
        policy_btn('Edit Tags', invokes_alert=True)
        fill(edit_tags_form, {'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')


class CatalogBundle(Updateable, Pretty):
    pretty_attrs = ['name', 'catalog', 'dialog']

    def __init__(self, name=None, description=None,
                 display_in=False, catalog=None,
                 dialog=None):
        self.name = name
        self.description = description
        self.display_in = display_in
        self.catalog = catalog
        self.dialog = dialog

    def create(self, cat_items):
        sel.force_navigate('catalog_bundle_new')
        fill(basic_info_form, {'name_text': self.name,
                               'description_text': self.description,
                               'display_checkbox': self.display_in,
                               'select_catalog': self.catalog,
                               'select_dialog': self.dialog})
        tabstrip.select_tab("Resources")
        for cat_item in cat_items:
            fill(resources_form, {'choose_resource': cat_item})
        sel.click(resources_form.add_button)
        flash.assert_success_message('Catalog Bundle "%s" was added' %
                                     self.name)

    def update(self, updates):
        sel.force_navigate('catalog_bundle_edit',
                           context={'catalog': self.catalog,
                                    'catalog_bundle': self})
        fill(basic_info_form, {'name_text': updates.get('name', None),
                               'description_text':
                               updates.get('description', None)})
        tabstrip.select_tab("Resources")
        fill(resources_form, {'choose_resource':
                              updates.get('cat_item', None)},
             action=resources_form.save_button)
        flash.assert_success_message('Catalog Bundle "%s" was saved' %
                                     self.name)
