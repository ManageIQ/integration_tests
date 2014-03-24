import ui_navigate as nav
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Form, Select, fill, Table, tabstrip, Radio
from utils.update import Updateable
import cfme.web_ui.accordion as accordion
import cfme.web_ui.toolbar as tb
import functools
from collections import OrderedDict

tb_select = functools.partial(tb.select, "Configuration")

template_select_form = Form(
    fields=[
        ('template_table', Table('//div[@id="prov_vm_div"]//table[@class="style3"]')),
        ('add_button', "//img[@title='Add']"),
        ('cancel_button', '//*[@id="form_buttons"]/li[2]/img')
    ]
)


def catalog_item_in_table(catalog_item):
    return "//div[@class='objbox']//td[.='%s']" % catalog_item.name


def catalog_item_in_tree(catalog_item):
    return "//div[@id='sandt_tree_div']//td[@class='standartTreeRow']/span[.='%s']" % catalog_item.name


def _all_catalogitems_add_new(context):
    sel.click("//div[@id='sandt_tree_div']//td[.='All Catalog Items']")
    tb_select('Add a New Catalog Item')
    provider_type = context['provider_type']
    sel.select("//select[@id='st_prov_type']", provider_type)

# Forms
basic_info_form = Form(
    fields=[
        ('name_text', "//input[@id='name']"),
        ('description_text', "//input[@id='description']"),
        ('display_checkbox', "//input[@id='display']"),
        ('select_catalog', Select("//select[@id='catalog_id']")),
        ('select_dialog', Select("//select[@id='dialog_id']")),
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
        ]),
        ('Schedule', [
            ('power_on_vm', "//input[@id='schedule__vm_auto_start']"),
            ('retirement', Select('//select[@id="schedule__retirement"]')),
            ('retirement_warning', Select('//select[@id="schedule__retirement_warn"]')),
        ])
    ])
)

nav.add_branch(
    'services_catalogs',
    {'catalog_items': [nav.partial(accordion.click, 'Catalog Items'),
                       {'catalog_item_new': _all_catalogitems_add_new,
                        'catalog_item': [lambda ctx:
                                         sel.click(catalog_item_in_tree(ctx['catalog_item'])),
                                         {'catalog_item_edit':
                                          nav.partial(tb_select, "Edit this Item")}]}]})


class CatalogItem(Updateable):

    def __init__(self, item_type=None, name=None, description=None, display_in=False, catalog=None, dialog=None, long_desc=None,
    	catalog_name=None, provider=None, prov_data=None):
        self.item_type = item_type
        self.name = name
        self.description = description
        self.display_in = display_in
        self.catalog = catalog
        self.dialog = dialog
        self.long_desc = long_desc
        self.catalog_name = catalog_name
        self.provider = provider
        self.provisioning_data = prov_data

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
        request_form.fill(self.provisioning_data)
        sel.click(template_select_form.add_button)

