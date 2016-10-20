# -*- coding: utf-8 -*-
import functools

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui import AngularSelect, Form, Select, SplitTable, accordion,\
    fill, flash, form_buttons, Table, Tree, Input, Region, BootstrapTreeview
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.pretty import Pretty
from utils.update import Updateable

from widgetastic.utils import Fillable


accordion_tree = functools.partial(accordion.tree, "Service Dialogs")
cfg_btn = functools.partial(tb.select, "Configuration")
plus_btn = functools.partial(tb.select, "Add")
entry_table = Table({'5.6': "//div[@id='field_values_div']/form/table",
                     '5.5': "//div[@id='field_values_div']/form/fieldset/table"})
text_area_table = Table("//div[@id='dialog_field_div']/fieldset/table[@class='style1']")
text_area_table = Table({version.LOWEST: "//div[@id='dialog_field_div']/fieldset/table"
                        "[@class='style1']",
                    '5.5': "//div[@id='dialog_field_div']/div[@class='form-horizontal']"})
dynamic_tree = Tree("//div[@class='modal-content']/div/div/ul[@class='dynatree-container']")
bt_tree = BootstrapTreeview('automate_treebox')

label_form = Form(fields=[
    ('label', Input("label")),
    ('description_text', Input("description")),
    ('submit_button', Input("chkbx_submit")),
    ('cancel_button', Input("chkbx_cancel"))
])

tab_form = Form(fields=[
    ('tab_label', Input("tab_label")),
    ('tab_desc', Input("tab_description"))
])

box_form = Form(fields=[
    ('box_label', Input("group_label")),
    ('box_desc', Input("group_description"))
])

element_form = Form(fields=[
    ('ele_label', Input("field_label")),
    ('ele_name', Input("field_name")),
    ('ele_desc', Input("field_description")),
    ('choose_type', {
        version.LOWEST: Select("//select[@id='field_typ']"),
        "5.5": AngularSelect("field_typ")}),
    ('default_text_box', Input("field_default_value")),
    ('field_required', Input("field_required")),
    ('field_past_dates', Input("field_past_dates")),
    ('field_entry_point', Input("field_entry_point")),
    ('field_show_refresh_button', Input("field_show_refresh_button")),
    ('entry_value', Input("entry[value]")),
    ('entry_description', Input("entry[description]")),
    ('add_entry_button', Input("accept")),
    # This one too? vvv I could not find it in the form
    ('field_category', Select("//select[@id='field_category']")),
    ('text_area', {
        version.LOWEST: Input("field_default_value"),
        "5.5": AngularSelect("field_default_value")}),
    ('dynamic_chkbox', Input("field_dynamic")),
    ('apply_btn', '//a[@title="Apply"]')
])

common = Region(locators={
    "dialogs_table": {
        version.LOWEST: SplitTable(
            header_data=('//div[@class="xhdr"]/table/tbody', 1),
            body_data=('//div[@class="objbox"]/table/tbody', 1)),
        "5.5": Table("//div[@id='list_grid']/table")}})


class ServiceDialog(Updateable, Pretty, Navigatable, Fillable):
    pretty_attrs = ['label', 'description']

    def __init__(self, label=None, description=None,
                 submit=False, cancel=False,
                 tab_label=None, tab_desc=None,
                 box_label=None, box_desc=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.label = label
        self.description = description
        self.submit = submit
        self.cancel = cancel
        self.tab_label = tab_label
        self.tab_desc = tab_desc
        self.box_label = box_label
        self.box_desc = box_desc

    def as_fill_value(self):
        return self.label

    def add_element(self, *element_data):
        for each_element in element_data:
            plus_btn("Add a new Element to this Box")
            sel.wait_for_element(element_form.ele_label)
            # Workaround to refresh the fields, select other values (text area box and checkbox)and
            # then select "text box"
            fill(element_form, {'choose_type': "Text Area Box"})
            fill(element_form, {'choose_type': "Check Box"})
            fill(element_form, each_element)
            self.element_type(each_element)

    def create(self, *element_data):
        navigate_to(self, 'Add')
        fill(label_form, {'label': self.label,
                          'description_text': self.description,
                          'submit_button': self.submit,
                          'cancel_button': self.cancel,
                          'label': self.label})
        plus_btn("Add a new Tab to this Dialog")
        sel.wait_for_element(tab_form.tab_label)
        fill(tab_form, {'tab_label': self.tab_label,
                        'tab_desc': self.tab_desc})
        plus_btn("Add a new Box to this Tab")
        sel.wait_for_element(box_form.box_label)
        fill(box_form, {'box_label': self.box_label,
                        'box_desc': self.box_desc})
        self.add_element(*element_data)
        sel.click(form_buttons.add)
        flash.assert_success_message('Dialog "{}" was added'.format(self.label))

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(label_form, {'name_text': updates.get('name', None),
                          'description_text': updates.get('description', None)})
        sel.click(form_buttons.save)
        flash.assert_no_errors()

    def update_element(self, second_element, element_data):
        navigate_to(self, 'Edit')
        if version.current_version() > "5.5":
            tree = accordion.tree("Dialog")
        else:
            tree = Tree("dialog_edit_treebox")
        tree.click_path(self.label, self.tab_label, self.box_label)
        self.add_element(second_element)
        list_ele = []
        list_ele.append(element_data.get("ele_label"))
        list_ele.append(second_element.get("ele_label"))
        tree.click_path(self.label, self.tab_label, self.box_label)
        ele_1 = self.element(list_ele[0])
        ele_2 = self.element(list_ele[1])
        sel.drag_and_drop(ele_1, ele_2)
        sel.click(form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        cfg_btn("Remove from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel)

    def element_type(self, each_element):
        choose_type = each_element.get("choose_type")
        dynamic_chkbox = each_element.get("dynamic_chkbox")
        if choose_type == "Drop Down List" or choose_type == "Radio Button":
            if not dynamic_chkbox:
                entry_table.click_cell(header='value', value='<New Entry>')
                fill(element_form, {'entry_value': "Yes",
                                    'entry_description': "entry_desc"},
                    action=element_form.add_entry_button)
            else:
                node1 = "InspectMe"
                sel.click(element_form.field_entry_point)
                if version.current_version() < "5.7":
                    dynamic_tree.click_path("Datastore", "new_domain", "System", "Request", node1)
                else:
                    bt_tree.click_path("Datastore", "new_domain", "System", "Request", node1)
                sel.click(element_form.apply_btn)
                fill(element_form, {'field_show_refresh_button': True})
        if choose_type == "Text Area Box":
            text_area_table.click_cell(1, value="Default text")

    def element(self, element_data):
        return sel.element('//div[@class="panel-heading"]'
            '[contains(normalize-space(.), "{}")]/..'.format(element_data))

    def reorder_elements(self, tab, box, *element_data):
        navigate_to(self, 'Edit')
        tree = accordion.tree("Dialog")
        tree.click_path(self.label, tab, box)
        list_ele = []
        for each_element in element_data:
            list_ele.append(each_element.get("ele_label"))
        ele_1 = self.element(list_ele[0])
        ele_2 = self.element(list_ele[1])
        sel.drag_and_drop(ele_1, ele_2)
        sel.click(form_buttons.save)
        flash.assert_no_errors()


@navigator.register(ServiceDialog, 'All')
class ServiceDialogAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Automate', 'Customization')(None)

    def resetter(self):
        accordion.tree("Service Dialogs", "All Dialogs")


@navigator.register(ServiceDialog, 'Add')
class ServiceDialogNew(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a new Dialog')
        sel.wait_for_element(label_form.label)


@navigator.register(ServiceDialog, 'Details')
class ServiceDialogDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree('Service Dialogs', "All Dialogs", self.obj.label)


@navigator.register(ServiceDialog, 'Edit')
class ServiceDialogEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn("Edit this Dialog")
