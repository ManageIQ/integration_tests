"""Service Catalog item for EC2 , does not provision any VM just create a
catalog item of type "Amazon

"""
import functools

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui.menu import nav
import cfme.web_ui as web_ui
import cfme.web_ui.toolbar as tb
from cfme.provisioning import provisioning_form as request_form
from cfme.web_ui import accordion, tabstrip, Form, Table, Select, fill,\
    flash, form_buttons, Input, Tree, AngularSelect
from utils.update import Updateable
from utils import version
from utils.pretty import Pretty


tb_select = functools.partial(tb.select, "Configuration")
catalog_item_tree = web_ui.Tree('//div[@id="sandt_treebox"]//ul')
dynamic_tree = Tree("//div[@id='basic_info_div']//ul[@class='dynatree-container']")

template_select_form = Form(
    fields=[
        ('template_table', Table('//div[@id="prov_vm_div"]/table')),
        ('add_button', form_buttons.add),
        ('cancel_button', form_buttons.cancel)
    ]
)

# Forms
basic_info_form = Form(
    fields=[
        ('name_text', Input("name")),
        ('description_text', Input("description")),
        ('display_checkbox', Input("display")),
        ('select_catalog', {
            version.LOWEST: Select("//select[@id='catalog_id']"),
            '5.5': AngularSelect('catalog_id')}),
        ('select_dialog', {
            version.LOWEST: Select("//select[@id='dialog_id']"),
            '5.5': AngularSelect('dialog_id')}),
        ('edit_button', form_buttons.save),
        ('field_entry_point', Input("fqname")),
        ('apply_btn', {
            version.LOWEST: '//a[@title="Apply"]',
            '5.5': '//a[normalize-space(.)="Apply"]'})
    ])


detail_form = Form(
    fields=[
        ('long_desc', "//textarea[@id='long_description']")
    ])


def _all_catalogitems_add_new(context):
    accordion.tree('Catalog Items', 'All Catalog Items')
    tb_select('Add a New Catalog Item')
    provider_type = context['provider_type']
    sel.select("//select[@id='st_prov_type']", provider_type)


def _all_catalogbundle_add_new(context):
    sel.click("//div[@id='sandt_tree_div']//td[normalize-space(.)='All Catalog Items']")
    tb_select('Add a New Catalog Bundle')


nav.add_branch(
    'services_catalogs',
    {'catalog_items': [nav.partial(accordion.click, 'Catalog Items'),
        {'catalog_item_new': _all_catalogitems_add_new,
         'catalog_item': [lambda ctx: accordion.tree('Catalog Items', 'All Catalog Items',
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
                 instance_type=None, availability_zone=None, cloud_tenant=None, cloud_network=None,
                 security_groups=None, provider=None, provider_mgmt=None, guest_keypair=None):
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
        self.cloud_tenant = cloud_tenant
        self.cloud_network = cloud_network
        self.security_groups = security_groups
        self.provider = provider
        self.provider_mgmt = provider_mgmt
        self.guest_keypair = guest_keypair

    def create(self):
        domain = "ManageIQ (Locked)"
        sel.force_navigate('catalog_item_new', context={'provider_type': self.item_type})
        sel.wait_for_element(basic_info_form.name_text)
        fill(basic_info_form, {'name_text': self.name,
                               'description_text': self.description,
                               'display_checkbox': self.display_in,
                               'select_catalog': self.catalog,
                               'select_dialog': self.dialog})
        if self.item_type != "Orchestration":
            sel.click(basic_info_form.field_entry_point)
            dynamic_tree.click_path("Datastore", domain, "Service", "Provisioning",
                                    "StateMachines", "ServiceProvision_Template", "default")
            sel.click(basic_info_form.apply_btn)
        tabstrip.select_tab("Request Info")
        # Address BZ1321631
        tabstrip.select_tab("Environment")
        tabstrip.select_tab("Catalog")
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
            'cloud_tenant': self.cloud_tenant,
            'cloud_network': self.cloud_network,
            'security_groups': self.security_groups[0],  # not supporting multiselect now,
                                                         # just take first value
        })
        sel.click(template_select_form.add_button)
        flash.assert_success_message('Service Catalog Item "{}" was added'.format(self.name))
