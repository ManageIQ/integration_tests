# -*- coding: utf-8 -*-
import functools

from cfme.web_ui import menu
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui import Form, Select, SplitTable, accordion,\
    fill, flash, form_buttons, Table, Tree
from utils.update import Updateable
from utils.pretty import Pretty

accordion_tree = functools.partial(accordion.tree, "Service Dialogs")
cfg_btn = functools.partial(tb.select, "Configuration")
plus_btn = functools.partial(tb.select, "Add")
entry_table = Table("//div[@id='field_values_div']/form/fieldset/table[@class='style3']")
text_area_table = Table("//div[@id='dialog_field_div']/fieldset/table[@class='style1']")

label_form = Form(fields=[
    ('label', "//input[@id='label']"),
    ('description_text', "//input[@id='description']"),
    ('submit_button', "//input[@id='chkbx_submit']"),
    ('cancel_button', "//input[@id='chkbx_cancel']")
])

tab_form = Form(fields=[
    ('tab_label', "//input[@id='tab_label']"),
    ('tab_desc', "//input[@id='tab_description']")
])

box_form = Form(fields=[
    ('box_label', "//input[@id='group_label']"),
    ('box_desc', "//input[@id='group_description']")
])

element_form = Form(fields=[
    ('ele_label', "//input[@id='field_label']"),
    ('ele_name', "//input[@id='field_name']"),
    ('ele_desc', "//input[@id='field_description']"),
    ('choose_type', Select("//select[@id='field_typ']")),
    ('default_text_box', "//input[@id='field_default_value']"),
    ('field_required', "//input[@id='field_required']"),
    ('field_past_dates', "//input[@id='field_past_dates']"),
    ('field_entry_point', "//input[@id='field_entry_point']"),
    ('field_show_refresh_button', "//input[@id='field_show_refresh_button']"),
    ('entry_value', "//input[@id='entry_value']"),
    ('entry_description', "//input[@id='entry_description']"),
    ('field_category', Select("//select[@id='field_category']")),
    ('text_area', "//textarea[@id='field_default_value']"),
])

dialogs_table = SplitTable(
    header_data=('//div[@class="xhdr"]/table/tbody', 1),
    body_data=('//div[@class="objbox"]/table/tbody', 1))


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
            lambda ctx: accordion.tree('Service Dialogs', ctx['dialog'].label),
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
        for each_element in element_data:
            plus_btn("Add a new Element to this Box")
            sel.wait_for_element(element_form.ele_label)
            fill(element_form, each_element)
            self.element_type(each_element)
        sel.click(form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate('service_dialog_edit', context={'dialog': self})
        fill(label_form, {'name_text': updates.get('name', None),
                          'description_text': updates.get('description', None)})
        sel.click(form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        sel.force_navigate('service_dialog', context={'dialog': self})
        cfg_btn("Remove from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel)

    def element_type(self, each_element):
        choose_type = each_element.get("choose_type")
        if choose_type == "Drop Down List" or choose_type == "Radio Button":
            entry_table.click_cell(header='value', value='<New Entry>')
            fill(element_form, {'entry_value': "Yes",
                                'entry_description': "entry_desc"})
        if choose_type == "Text Area Box":
            text_area_table.click_cell(1, value="Default text")

    def element(self, element_data):
        return sel.element('//div[@class="modbox"]/h2[@class="modtitle"]'
                          '[contains(normalize-space(.), "{}")]/..'.format(element_data))

    def reorder_elements(self, box, *element_data):
        sel.force_navigate('service_dialog_edit', context={'dialog': self})
        tree = Tree("//div[@class='dhxcont_global_content_area']"
                    "[not(contains(@style, 'display: none'))]/div/div/div/div"
                    "/ul[@class='dynatree-container']")
        tree.click_path(box)
        list_ele = []
        for each_element in element_data:
            list_ele.append(each_element.get("ele_label"))
        ele_1 = self.element(list_ele[0])
        ele_2 = self.element(list_ele[1])
        sel.drag_and_drop(ele_1, ele_2)
        sel.click(form_buttons.save)
        flash.assert_no_errors()
