# -*- coding: utf-8 -*-
import functools

from cfme.web_ui import menu

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui import Form, Select, SplitTable, accordion,\
    fill, flash, form_buttons, Table
from utils import version
from utils.update import Updateable
from utils.pretty import Pretty

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
    ('text_area', "//input[@id='field_default_value']"),
])

dialogs_table = SplitTable(
    header_data=("//div[@id='records_div']//table[contains(@class, 'hdr')]", 1),
    body_data=("//div[@id='records_div']//div[contains(@class, 'objbox')]/table", 1))


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
                 box_label=None, box_desc=None,
                 ele_label=None, ele_name=None,
                 ele_desc=None, choose_type=None, default_text_box=None,
                 field_required=None, field_past_dates=None, field_entry_point=None,
                 field_show_refresh_button=None, entry_value=None,
                 entry_desc=None, field_category=None, text_area=None):
        self.label = label
        self.description = description
        self.submit = submit
        self.cancel = cancel
        self.tab_label = tab_label
        self.tab_desc = tab_desc
        self.box_label = box_label
        self.box_desc = box_desc
        self.ele_label = ele_label
        self.ele_name = ele_name
        self.ele_desc = ele_desc
        self.choose_type = choose_type
        self.default_text_box = default_text_box
        self.field_required = field_required
        self.field_past_dates = field_past_dates
        self.field_entry_point = field_entry_point
        self.field_show_refresh_button = field_show_refresh_button
        self.entry_value = entry_value
        self.entry_desc = entry_desc
        self.field_category = field_category
        self.text_area = text_area

    def create(self):
        sel.force_navigate('service_dialog_new')
        fill(label_form, {'label': self.label,
                          'description_text': self.description,
                          'submit_button': self.submit,
                          'cancel_button': self.cancel})

        if self.tab_label is not None:
            btn_marker = version.pick({
                version.LOWEST: "Add a New Tab to this Dialog",
                '5.3': "Add a new Tab to this Dialog"
            })
            plus_btn(btn_marker)
            sel.wait_for_element(tab_form.tab_label)
            fill(tab_form, {'tab_label': self.tab_label,
                            'tab_desc': self.tab_desc})

        if self.box_label is not None:
            btn_marker = version.pick({
                version.LOWEST: "Add a New Box to this Tab",
                '5.3': "Add a new Box to this Tab"
            })
            plus_btn(btn_marker)
            sel.wait_for_element(box_form.box_label)
            fill(box_form, {'box_label': self.box_label,
                            'box_desc': self.box_desc})

        if self.ele_label is not None:
            btn_marker = version.pick({
                version.LOWEST: "Add a New Element to this Box",
                '5.3': "Add a new Element to this Box"
            })
            plus_btn(btn_marker)
            sel.wait_for_element(element_form.ele_label)
            fill(element_form, {'ele_label': self.ele_label,
                                'ele_name': self.ele_name,
                                'ele_desc': self.ele_desc,
                                'choose_type': self.choose_type,
                                'field_category': self.field_category,
                                'default_text_box': self.default_text_box,
                                'field_required': self.field_required,
                                'field_past_dates': self.field_past_dates,
                                'field_entry_point': self.field_entry_point,
                                'field_show_refresh_button': self.field_show_refresh_button})
            self.element_type()
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
        flash.assert_no_errors()

    def element_type(self):
        if self.choose_type == "Drop Down List" or self.choose_type == "Radio Button":
            entry_table.click_cell(header='value', value='<New Entry>')
            fill(element_form, {'entry_value': self.entry_value,
                                'entry_description': self.entry_desc})
        if self.choose_type == "Text Area Box":
            text_area_table.click_cell(1, value=self.text_area)
