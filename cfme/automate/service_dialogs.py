# -*- coding: utf-8 -*-
import functools

from cfme.web_ui import menu
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui import AngularSelect, Form, Select, SplitTable, accordion,\
    fill, flash, form_buttons, Table, Tree, Input, Region
from utils.update import Updateable
from utils.pretty import Pretty
from utils import version

accordion_tree = functools.partial(accordion.tree, "Service Dialogs")
cfg_btn = functools.partial(tb.select, "Configuration")
plus_btn = functools.partial(tb.select, "Add")
entry_table = Table("//div[@id='field_values_div']/form/fieldset/table")
text_area_table = Table("//div[@id='dialog_field_div']/fieldset/table[@class='style1']")
text_area_table = Table({version.LOWEST: "//div[@id='dialog_field_div']/fieldset/table"
                        "[@class='style1']",
                    '5.5': "//div[@id='dialog_field_div']/div[@class='form-horizontal']"})
dynamic_tree = Tree({version.LOWEST: "//div[@class='dhxcont_global_content_area']"
                                     "[not(contains(@style, 'display: none'))]/div/div/div/div/div"
                                     "/fieldset/div/ul[@class='dynatree-container']",
                    '5.4': "//div[@class='dhxcont_global_content_area']"
                           "[not(contains(@style, 'display: none'))]/div/div/div/div/div/div"
                           "/div/div/div/ul[@class='dynatree-container']",
                    '5.5': "//div[@class='modal-content']/div/div/ul[@class='dynatree-container']"})

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


def _all_servicedialogs_add_new(context):
    cfg_btn('Add a new Dialog')
    sel.wait_for_element(label_form.label)

menu.nav.add_branch(
    'automate_customization',
    {
        'service_dialogs':
        [
            lambda _: accordion.tree("Service Dialogs", "All Dialogs"),
            {
                'service_dialog_new': _all_servicedialogs_add_new
            }
        ],
        'service_dialog':
        [
            lambda ctx: accordion.tree('Service Dialogs', "All Dialogs", ctx['dialog'].label),
            {
                'service_dialog_edit': menu.nav.partial(cfg_btn, "Edit this Dialog")
            }
        ]
    }
)


class ServiceDialog(Updateable, Pretty):
    pretty_attrs = ['label', 'description']

    def __init__(self, label=None, description=None,
                 submit=False, cancel=False,
                 tab_label=None, tab_desc=None,
                 box_label=None, box_desc=None):
        self.label = label
        self.description = description
        self.submit = submit
        self.cancel = cancel
        self.tab_label = tab_label
        self.tab_desc = tab_desc
        self.box_label = box_label
        self.box_desc = box_desc

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
        sel.force_navigate('service_dialog_new')
        fill(label_form, {'label': self.label,
                          'description_text': self.description,
                          'submit_button': self.submit,
                          'cancel_button': self.cancel})
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
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate('service_dialog_edit', context={'dialog': self})
        fill(label_form, {'name_text': updates.get('name', None),
                          'description_text': updates.get('description', None)})
        sel.click(form_buttons.save)
        flash.assert_no_errors()

    def update_element(self, second_element, element_data):
        sel.force_navigate('service_dialog_edit', context={'dialog': self})
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
        sel.force_navigate('service_dialog', context={'dialog': self})
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
                dynamic_tree.click_path("Datastore", "new_domain", "System", "Request", node1)
                sel.click(element_form.apply_btn)
                fill(element_form, {'field_show_refresh_button': True})
        if choose_type == "Text Area Box":
            text_area_table.click_cell(1, value="Default text")

    def element(self, element_data):
        return sel.element(version.pick({
            '5.5': '//div[@class="panel-heading"]/h3[@class="panel-title"]'
            '[contains(normalize-space(.), "{}")]/..'.format(element_data),
            '5.4': '//div[@class="modbox"]/h2[@class="modtitle"]'
            '[contains(normalize-space(.), "{}")]/..'.format(element_data)}))

    def reorder_elements(self, tab, box, *element_data):
        sel.force_navigate('service_dialog_edit', context={'dialog': self})
        if version.current_version() > "5.5":
            tree = accordion.tree("Dialog")
        else:
            tree = Tree("dialog_edit_treebox")
        tree.click_path(self.label, tab, box)
        list_ele = []
        for each_element in element_data:
            list_ele.append(each_element.get("ele_label"))
        ele_1 = self.element(list_ele[0])
        ele_2 = self.element(list_ele[1])
        sel.drag_and_drop(ele_1, ele_2)
        sel.click(form_buttons.save)
        flash.assert_no_errors()
