# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from functools import partial

from cfme import web_ui
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, flash, form_buttons, menu, Input
from cfme.web_ui import toolbar as tb
from utils.update import Updateable
from utils.pretty import Pretty
from utils.blockers import BZ

cfg_btn = partial(tb.select, "Configuration")
catalog_tree = partial(accordion.tree, "Catalogs")

item_multiselect = web_ui.MultiSelect(
    "//select[@id='available_fields']",
    "//select[@id='selected_fields']",
    "//div[@id='column_lists']//a[contains(@href, 'button=right')]/img",
    "//div[@id='column_lists']//a[contains(@href, 'button=left')]/img")

form = web_ui.Form(
    fields=[('name_text', Input("name")),
            ('description_text', Input("description")),
            ('button_multiselect', item_multiselect),
            ('add_button', form_buttons.add),
            ('save_button', form_buttons.save),
            ('cancel_button', form_buttons.cancel)])

item_form = web_ui.Form(
    fields=[('type_select', "//select[@id='st_prov_type']"),
            ('name_text', Input("name")),
            ('description_text', Input("description")),
            ('display_checkbox', Input("display")),
            ('add_button', form_buttons.add)])


def _all_catalogs_add_new(_):
    if BZ(1213863).blocks:
        sel.pytest.skip("Blocker on the bug 1213863")
    catalog_tree('All Catalogs')
    cfg_btn('Add a New Catalog')


menu.nav.add_branch(
    'services_catalogs',
    {
        'catalogs':
        [
            lambda _: accordion.click('Catalogs'),
            {
                'catalog_new': _all_catalogs_add_new,
                'catalog':
                [
                    lambda ctx: catalog_tree('All Catalogs', ctx['catalog'].name),
                    {
                        'catalog_edit': lambda _: cfg_btn("Edit this Item")
                    }
                ]
            }
        ]
    }
)


class Catalog(Updateable, Pretty):
    """Represents a Catalog"""
    pretty_attrs = ['name', 'items']

    def __init__(self, name=None, description=None, items=None):
        self.name = name
        self.description = description
        self.items = items

    def __str__(self):
        return self.name

    def create(self):
        sel.force_navigate('catalog_new')
        sel.wait_for_element(form.name_text)
        web_ui.fill(form, {'name_text': self.name,
                           'description_text': self.description,
                           'button_multiselect': self.items},
                    action=form.add_button)
        flash_str = 'Catalog "{}" was saved'
        flash.assert_success_message(flash_str.format(self.name))

    def update(self, updates):
        sel.force_navigate('catalog_edit', context={'catalog': self})
        web_ui.fill(form, {'name_text': updates.get('name', None),
                           'description_text': updates.get('description', None),
                           'button_multiselect': updates.get('items', None)},
                    action=form.save_button)
        flash.assert_success_message('Catalog "{}" was saved'.format(self.name))

    def delete(self):
        sel.force_navigate('catalog', context={'catalog': self})
        cfg_btn("Remove Item from the VMDB", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message(
            'Catalog "{}": Delete successful'.format(self.description or self.name))

    @property
    def exists(self):
        try:
            sel.force_navigate('catalog', context={'catalog': self})
            return True
        except CandidateNotFound:
            return False
