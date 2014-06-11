import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.accordion as accordion
import cfme.web_ui.flash as flash
import cfme.web_ui as web_ui
import cfme.web_ui.menu  # load the menu nav endpoints
import cfme.web_ui.toolbar as tb
import ui_navigate as nav
import functools
from utils.update import Updateable

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

item_form = web_ui.Form(
    fields=
    [('type_select', "//select[@id='st_prov_type']"),
     ('name_text', "//input[@id='name']"),
     ('description_text', "//input[@id='description']"),
     ('display_checkbox', "//input[@id='display']"),
     ('add_button', "//img[@title='Add']")])


def _all_catalogs_add_new(_):
    accordion.tree('Catalogs', 'All Catalogs')
    tb_select('Add a New Catalog')


nav.add_branch(
    'services_catalogs',
    {'catalogs': [nav.partial(accordion.click, 'Catalogs'),
                  {'catalog_new': _all_catalogs_add_new,
                   'catalog': [lambda ctx: accordion.tree('Catalogs', 'All Catalogs',
                                                          ctx['catalog'].name),
                               {'catalog_edit': nav.partial(tb_select, "Edit this Item")}]}]})


class Catalog(Updateable):
    """Represents a Catalog"""

    def __init__(self, name=None, description=None, items=None):
        self.name = name
        self.description = description
        self.items = items

    def create(self):
        sel.force_navigate('catalog_new')
        web_ui.fill(form, {'name_text': self.name,
                           'description_text': self.description,
                           'button_multiselect': self.items},
                    action=form.add_button)
        flash.assert_success_message('ServiceTemplateCatalog "{}" was saved'.format(self.name))

    def update(self, updates):
        sel.force_navigate('catalog_edit', context={'catalog': self})
        web_ui.fill(form, {'name_text': updates.get('name', None),
                           'description_text': updates.get('description', None),
                           'button_multiselect': updates.get('items', None)},
                    action=form.save_button)
        flash.assert_success_message('ServiceTemplateCatalog "{}" was saved'.format(self.name))

    def delete(self):
        sel.force_navigate('catalog', context={'catalog': self})
        tb_select("Remove Item from the VMDB", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Catalog "{}": Delete successful'.format(self.description))
