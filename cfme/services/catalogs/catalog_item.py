import cfme.web_ui.accordion as accordion
import cfme.web_ui as web_ui
import cfme.web_ui.menu  # load the menu nav endpoints
import cfme.web_ui.toolbar as tb
import ui_navigate as nav
import functools
import cfme.fixtures.pytest_selenium as sel
from collections import OrderedDict
from cfme.web_ui import tabstrip
from cfme.infrastructure.provisioning import provisioning_form
from cfme.web_ui import Select, fill
from time import sleep


assert cfme.web_ui.menu  # to placate flake8 (otherwise menu import is unused)

tb_select = functools.partial(tb.select, "Configuration")

prov_select_form = web_ui.Form(
    fields=
    [('type_select', Select("//select[@id='st_prov_type']"))]
)

catalog_item_form = tabstrip.TabStripForm(
    fields=[
        ('add_button', "//img[@title='Add']"),
        ('cancel_button', '//*[@id="form_buttons"]/li[2]/img')
    ],
    tab_fields=OrderedDict([
        ('Basic Info', [
            ('name_text', "//input[@id='name']"),
            ('description_text', "//input[@id='description']"),
            ('display_checkbox', "//input[@id='display']"),
            ('select_catalog', "select#catalog_id"),
            ('select_dialog', "select#dialog_id]")
        ]),
        ('Details', [
            ('long_desc', "//textarea[@id='long_description']")
        ]),
        ('Request Info', [
            ('provisioning_form', provisioning_form)
        ])
    ])
)


def catalog_item_in_table(catalog_item):
    return "//div[@class='objbox']//td[.='%s']" % catalog_item.name


def catalog_item_in_tree(catalog_item):
    return "//div[@id='sandt_tree_div']//td[@class='standartTreeRow']/span[.='%s']" % catalog_item.name


def _all_catalogitems_add_new(context):
    sel.click("//div[@id='sandt_tree_div']//td[.='All Catalog Items']")
    tb_select('Add a New Catalog Item')
    provider = context['provider']
    sleep(5)
    fill(
        prov_select_form,
        {"type_select": provider}
    )

nav.add_branch(
    'services_catalogs',
    {'catalog_items': [nav.partial(accordion.click, 'Catalog Items'),
                       {'catalog_item_new': _all_catalogitems_add_new,
                        'catalog_item': [lambda ctx:
                                         sel.click(catalog_item_in_tree(ctx['catalog_item'])),
                                         {'catalog_item_edit':
                                          nav.partial(tb_select, "Edit this Item")}]}]})