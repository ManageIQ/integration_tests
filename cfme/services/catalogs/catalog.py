import cfme.web_ui.accordion as accordion
import cfme.web_ui as web_ui
import cfme.web_ui.menu  # load the menu nav endpoints
import cfme.web_ui.toolbar as tb
import ui_navigate as nav
import functools
import cfme.fixtures.pytest_selenium as sel

assert cfme.web_ui.menu  # to placate flake8 (otherwise menu import is unused)

tb_select = functools.partial(tb.select, "Configuration")

item_multiselect = web_ui.MultiSelect(
    "//select[@id='available_fields']",
    "//select[@id='selected_fields']",
    "//div[@id='column_lists']//a[contains(@href, 'button=right')]/img",
    "//div[@id='column_lists']//a[contains(@href, 'button=left')]/img")

form = web_ui.Form(
    fields=
    [('name_text', "//input[@id='name']"),
     ('description_text', "//input[@id='description']"),
     ('button_multiselect', item_multiselect),
     ('add_button', "//img[@title='Add']"),
     ('save_button', "//img[@title='Save Changes']"),
     ('cancel_button', "//img[@title='Cancel']")])


def catalog_in_table(catalog):
    return "//div[@class='objbox']//td[.='%s']" % catalog.name


def catalog_in_tree(catalog):
    return "//div[@id='stcat_tree_div']//td[@class='standartTreeRow']/span[.='%s']" % catalog.name
    
nav.add_branch(
    'services_catalogs',
    {'catalogs': [nav.partial(accordion.click, 'Catalogs'),
                  {'catalog_new': functools.partial(tb_select, 'Add a New Catalog'),
                   'catalog': [lambda ctx: sel.click(catalog_in_tree(ctx['catalog'])),
                               {'catalog_edit': nav.partial(tb_select, "Edit this Item")}]}]})
