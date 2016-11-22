# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToAttribute, NavigateToSibling

from cfme import web_ui
from cfme.exceptions import DestinationNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, flash, form_buttons, Input
from cfme.web_ui import toolbar as tb, paginator, CheckboxTable, match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.blockers import BZ
from utils.pretty import Pretty
from utils.update import Updateable
from utils import version


cfg_btn = partial(tb.select, "Configuration")
catalog_tree = partial(accordion.tree, "Catalogs")

listview_table = CheckboxTable(table_locator='//div[@id="list_grid"]/table')

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

match_page = partial(match_location, controller='catalog', title='Catalogs')


def _all_catalogs_add_new(_):
    if BZ(1213863).blocks:
        sel.pytest.skip("Blocker on the bug 1213863")
    catalog_tree('All Catalogs')
    cfg_btn('Add a New Catalog')


class Catalog(Updateable, Pretty, Navigatable):
    """Represents a Catalog"""
    pretty_attrs = ['name', 'items']

    def __init__(self, name=None, description=None, items=None, appliance=None):
        self.name = name
        self.description = description
        self.items = items
        Navigatable.__init__(self, appliance=appliance)

    def __str__(self):
        return self.name

    def create(self):
        navigate_to(self, 'Add')
        web_ui.fill(form, {'name_text': self.name,
                           'description_text': self.description,
                           'button_multiselect': self.items},
                    action=form.add_button)
        flash_str = 'Catalog "{}" was saved'
        flash.assert_success_message(flash_str.format(self.name))

    def update(self, updates):
        navigate_to(self, 'Edit')
        web_ui.fill(form, {'name_text': updates.get('name', None),
                           'description_text': updates.get('description', None),
                           'button_multiselect': updates.get('items', None)},
                    action=form.save_button)
        flash.assert_success_message('Catalog "{}" was saved'.format(self.name))

    def delete(self, from_dest='All'):
        """
        Delete the catalog, starting from the destination provided by from_dest
        Throws cfme.DestinationNotFound exception

        :param from_dest: A valid navigation destination to start the delete from
        :return: none
        """
        if from_dest in navigator.list_destinations(self):
            navigate_to(self, from_dest)
        else:
            msg = 'cfme.services.catalogs.catalog does not have destination {}'.format(from_dest)
            raise DestinationNotFound(msg)

        # Delete using the appropriate method
        if from_dest == 'All':
            # Select the row to delete, assuming default List View for All
            listview_table.select_row_by_cells({'Name': self.name, 'Description': self.description})
            cfg_btn(version.pick({version.LOWEST: 'Remove Items from the VMDB',
                    '5.7': 'Remove Catalogs'}), invokes_alert=True)
        elif from_dest == 'Details':
            cfg_btn(version.pick({version.LOWEST: 'Remove Item from the VMDB',
                    '5.7': 'Remove Catalog'}), invokes_alert=True)

        sel.handle_alert()
        flash.assert_success_message(
            'Catalog "{}": Delete successful'.format(self.description or self.name))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        # web_ui.Table.click_row_by_cells throws a NameError exception on no match
        except NameError:
            return False


@navigator.register(Catalog, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='All Catalogs')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Services', 'Catalogs')(None)
        tree = accordion.tree('Catalogs')
        tree.click_path('All Catalogs')

    def resetter(self):
        # Default list view
        tb.select('List View')
        if paginator.page_controls_exist():
            # Make sure nothing is selected
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(Catalog, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='Adding a new Catalog')

    def step(self):
        cfg_btn('Add a New Catalog')


@navigator.register(Catalog, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        # header text as separate var to reduce quote escaping
        return match_page(summary='Catalog "{}"'.format(self.obj.name))

    def step(self):
        # Best effort to make sure the catalog is in the list
        if paginator.page_controls_exist():
            paginator.results_per_page(1000)
        listview_table.click_row_by_cells(
            {'Name': self.obj.name, 'Description': self.obj.description})


@navigator.register(Catalog, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        match_page(summary='Editing Catalog "{}"'.format(self.obj.name))

    def step(self):
        cfg_btn('Edit this Item')
