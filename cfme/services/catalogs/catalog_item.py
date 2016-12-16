# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.exceptions import DestinationNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.provisioning import provisioning_form as request_form
from cfme.web_ui import Form, Select, Table, accordion, fill, paginator, \
    flash, form_buttons, tabstrip, DHTMLSelect, Input, Tree, AngularSelect, \
    BootstrapTreeview, toolbar as tb, match_location, CheckboxTable
from utils import version, fakeobject_or_object
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from utils.update import Updateable
from utils.pretty import Pretty
from utils.version import current_version

cfg_btn = partial(tb.select, "Configuration")
policy_btn = partial(tb.select, "Policy")

accordion_tree = partial(accordion.tree, "Catalog Items")
dynamic_tree = Tree("//div[@id='basic_info_div']//ul[@class='dynatree-container']")
entry_tree = BootstrapTreeview('automate_treebox')
listview_table = CheckboxTable(table_locator='//div[@id="list_grid"]/table')

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
        ('select_orch_template', {
            version.LOWEST: Select("//select[@id='template_id']"),
            '5.5': AngularSelect('template_id')}),
        ('select_provider', {
            version.LOWEST: Select("//select[@id='manager_id']"),
            '5.5': AngularSelect('manager_id')}),
        ('select_config_template', {
            version.LOWEST: Select("//select[@id='template_id']"),
            '5.5': AngularSelect('template_id')}),
        ('field_entry_point', Input("fqname")),
        ('edit_button', form_buttons.save),
        ('apply_btn', {
            version.LOWEST: '//a[@title="Apply"]',
            '5.5.0.6': '//a[normalize-space(.)="Apply"]'})
    ])

# TODO: Replace with Taggable
edit_tags_form = Form(
    fields=[
        ("select_tag", {
            version.LOWEST: Select("select#tag_cat"),
            '5.5': AngularSelect('tag_cat')}),
        ("select_value", {
            version.LOWEST: Select("select#tag_add"),
            '5.5': AngularSelect('tag_add')})
    ])

detail_form = Form(
    fields=[
        ('long_desc', Input('long_description')),
    ])

resources_form = Form(
    fields=[
        ('choose_resource', Select("//select[@id='resource_id']")),
        ('add_button', form_buttons.add),
        ('save_button', form_buttons.save)
    ])

button_group_form = Form(
    fields=[
        ('btn_group_text', Input("name")),
        ('btn_group_hvr_text', Input("description")),
        ('add_button', form_buttons.add)
    ])

button_form = Form(
    fields=[
        ('btn_text', Input("name")),
        ('btn_hvr_text', Input("description")),
        ('select_dialog', Select("//select[@id='dialog_id']")),
        ('system_process', Select("//select[@id='instance_name']")),
        ('request', Input("object_request")),
        ('add_button', form_buttons.add)
    ])

match_page = partial(match_location, title='Catalogs', controller='catalog')


def nav_to_all():
    from cfme.web_ui.menu import nav
    nav._nav_to_fn('Services', 'Catalogs')(None)
    tree = accordion.tree('Catalog Items')
    tree.click_path('All Catalog Items')


class CatalogItem(Updateable, Pretty, Navigatable):
    pretty_attrs = ['name', 'item_type', 'catalog', 'catalog_name', 'provider', 'domain']

    def __init__(self, item_type=None, vm_name=None, name=None, description=None,
                 display_in=False, catalog=None, dialog=None,
                 catalog_name=None, orch_template=None, provider_type=None,
                 provider=None, config_template=None, prov_data=None, domain="ManageIQ (Locked)",
                 appliance=None):
        self.item_type = item_type
        self.vm_name = vm_name
        self.name = name
        self.description = description
        self.display_in = display_in
        self.catalog = catalog
        self.dialog = dialog
        self.catalog_name = catalog_name
        self.orch_template = orch_template
        self.provider = provider
        self.config_template = config_template
        self.provider_type = provider_type
        self.provisioning_data = prov_data
        self.domain = domain
        Navigatable.__init__(self, appliance=appliance)

    def __str__(self):
        return self.name

    def create(self):
        # Create has sequential forms, the first is only the provider type
        navigate_to(self, 'Add')
        sel.select("//select[@id='st_prov_type']",
                   self.item_type or 'Generic')
        sel.wait_for_element(basic_info_form.name_text)
        catalog = fakeobject_or_object(self.catalog, "name", "Unassigned")
        dialog = fakeobject_or_object(self.dialog, "name", "No Dialog")

        fill(basic_info_form, {'name_text': self.name,
                               'description_text': self.description,
                               'display_checkbox': self.display_in,
                               'select_catalog': catalog.name,
                               'select_dialog': dialog.name,
                               'select_orch_template': self.orch_template,
                               'select_provider': self.provider_type,
                               'select_config_template': self.config_template})
        if sel.text(basic_info_form.field_entry_point) == "":
            sel.click(basic_info_form.field_entry_point)
            if version.current_version() < "5.7":
                dynamic_tree.click_path("Datastore", self.domain, "Service", "Provisioning",
                                     "StateMachines", "ServiceProvision_Template", "default")
            else:
                entry_tree.click_path("Datastore", self.domain, "Service", "Provisioning",
                                     "StateMachines", "ServiceProvision_Template", "default")
            sel.click(basic_info_form.apply_btn)
        if self.catalog_name is not None and self.provisioning_data is not None:
            tabstrip.select_tab("Request Info")
            # Address BZ1321631
            tabstrip.select_tab("Environment")
            tabstrip.select_tab("Catalog")
            template = template_select_form.template_table.find_row_by_cells({
                'Name': self.catalog_name,
                'Provider': self.provider
            })
            sel.click(template)
            request_form.fill(self.provisioning_data)
        sel.click(template_select_form.add_button)

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(basic_info_form, {'name_text': updates.get('name', None),
                               'description_text':
                               updates.get('description', None)},
             action=basic_info_form.edit_button)
        flash.assert_success_message('Service Catalog Item "{}" was saved'.format(self.name))

    def delete(self, from_dest='All'):
        if from_dest in navigator.list_destinations(self):
            navigate_to(self, from_dest)
        else:
            msg = 'cfme.services.catalogs.catalog_item does not have destination {}'\
                .format(from_dest)
            raise DestinationNotFound(msg)
        if from_dest == 'All':
            # select the row for deletion
            listview_table.select_row_by_cells({'Name': self.name,
                                                'Description': self.description})
            cfg_btn(version.pick({version.LOWEST: 'Remove Items from the VMDB',
                '5.7': 'Remove Catalog Items'}), invokes_alert=True)
        if from_dest == 'Details':
            cfg_btn(version.pick({version.LOWEST: 'Remove Item from the VMDB',
                '5.7': 'Remove Catalog Item'}), invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message(version.pick(
            {version.LOWEST: 'The selected 1 Catalog Item were deleted',
                '5.7': 'The selected 1 Catalog Item was deleted'}))

    def add_button_group(self):
        navigate_to(self, 'Details')
        cfg_btn("Add a new Button Group", invokes_alert=True)
        sel.wait_for_element(button_group_form.btn_group_text)
        fill(button_group_form, {'btn_group_text': "group_text",
                                 'btn_group_hvr_text': "descr"})
        if current_version() > "5.5":
            select = AngularSelect("button_image")
            select.select_by_visible_text("Button Image 1")
        else:
            select = DHTMLSelect("div#button_div")
            select.select_by_value(1)
        sel.click(button_group_form.add_button)
        flash.assert_success_message('Buttons Group "descr" was added')

    def add_button(self):
        navigate_to(self, 'Details')
        cfg_btn('Add a new Button', invokes_alert=True)
        sel.wait_for_element(button_form.btn_text)
        fill(button_form, {'btn_text': "btn_text",
                           'btn_hvr_text': "btn_descr"})
        if current_version() > "5.5":
            select = AngularSelect("button_image")
            select.select_by_visible_text("Button Image 1")
        else:
            select = DHTMLSelect("div#button_div")
            select.select_by_value(2)
        fill(button_form, {'select_dialog': self.dialog,
                           'system_process': "Request",
                           'request': "InspectMe"})
        sel.click(button_form.add_button)
        flash.assert_success_message('Button "btn_descr" was added')

    def edit_tags(self, tag, value):
        navigate_to(self, 'Details')
        policy_btn('Edit Tags', invokes_alert=True)
        fill(edit_tags_form, {'select_tag': tag,
                              'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')


class CatalogBundle(Updateable, Pretty, Navigatable):
    pretty_attrs = ['name', 'catalog', 'dialog']

    def __init__(self, name=None, description=None, display_in=None, catalog=None, dialog=None,
                 appliance=None):
        self.name = name
        self.description = description
        self.display_in = display_in
        self.catalog = catalog
        self.dialog = dialog
        Navigatable.__init__(self, appliance=appliance)

    def __str__(self):
        return self.name

    def create(self, cat_items):
        navigate_to(self, 'Add')
        domain = "ManageIQ (Locked)"
        fill(basic_info_form, {'name_text': self.name,
                               'description_text': self.description,
                               'display_checkbox': self.display_in,
                               'select_catalog': str(self.catalog),
                               'select_dialog': str(self.dialog)})
        sel.click(basic_info_form.field_entry_point)
        if sel.text(basic_info_form.field_entry_point) == "":
            if version.current_version() < "5.7":
                dynamic_tree.click_path("Datastore", domain, "Service", "Provisioning",
                    "StateMachines", "ServiceProvision_Template", "default")
            else:
                entry_tree.click_path("Datastore", domain, "Service", "Provisioning",
                    "StateMachines", "ServiceProvision_Template", "default")
        sel.click(basic_info_form.apply_btn)
        tabstrip.select_tab("Resources")
        for cat_item in cat_items:
            fill(resources_form, {'choose_resource': cat_item})
        sel.click(resources_form.add_button)
        flash.assert_success_message('Catalog Bundle "{}" was added'.format(self.name))

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(basic_info_form, {'name_text': updates.get('name', None),
                               'description_text':
                               updates.get('description', None)})
        tabstrip.select_tab("Resources")
        fill(resources_form, {'choose_resource':
                              updates.get('cat_item', None)},
             action=resources_form.save_button)
        flash.assert_success_message('Catalog Bundle "{}" was saved'.format(self.name))


@navigator.register(CatalogItem, 'All')
class ItemAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='All Service Catalog Items')

    def step(self):
        nav_to_all()

    def resetter(self):
        tb.refresh()
        tb.select('List View')
        # Ensure no rows are checked
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(CatalogItem, 'Details')
class ItemDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    # No am_i_here() due to summary duplication between item and bundle

    def step(self):
        listview_table.click_row_by_cells({'Name': self.obj.name,
                                           'Description': self.obj.description,
                                           'Type': 'Item'})

    def resetter(self):
        tb.refresh()


@navigator.register(CatalogItem, 'Add')
class ItemAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='Adding a new Service Catalog Item')

    def step(self):
        cfg_btn('Add a New Catalog Item')


@navigator.register(CatalogItem, 'Edit')
class ItemEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='Editing Service Catalog Item "{}"'.format(self.obj.name))

    def step(self):
        cfg_btn('Edit this Item')


@navigator.register(CatalogBundle, 'All')
class BundleAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='All Service Catalog Items')

    def step(self):
        nav_to_all()

    def resetter(self):
        tb.refresh()
        tb.select('List View')
        # Ensure no rows are checked
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(CatalogBundle, 'Details')
class BundleDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    # No am_i_here() due to summary duplication between item and bundle

    def step(self):
        listview_table.click_row_by_cells({'Name': self.obj.name,
                                           'Description': self.obj.description,
                                           'Type': 'Bundle'})

    def resetter(self):
        tb.refresh()


@navigator.register(CatalogBundle, 'Add')
class BundleAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='Adding a new Catalog Bundle')

    def step(self):
        cfg_btn('Add a New Catalog Bundle')


@navigator.register(CatalogBundle, 'Edit')
class BundleEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='Editing Catalog Bundle "{}"'.format(self.obj.name))

    def step(self):
        cfg_btn('Edit this Item')
