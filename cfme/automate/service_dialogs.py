import functools

import ui_navigate as nav
from selenium.webdriver.common.by import By

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.accordion as accordion
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Form, fill, Select
from utils.update import Updateable


cfg_btn = functools.partial(tb.select, "Configuration")
plus_btn = functools.partial(tb.select, "Add")
message = (By.CSS_SELECTOR, "div#flash_msg_div")

label_form = Form(
    fields=
    [('label', (By.CSS_SELECTOR, "input#label")),
     ('description_text', (By.CSS_SELECTOR, "input#description")),
     ('submit_button', (By.CSS_SELECTOR, "input#chkbx_submit")),
     ('cancel_button', (By.CSS_SELECTOR, "input#chkbx_cancel"))])

tab_form = Form(
    fields=
    [('tab_label', (By.CSS_SELECTOR, "input#tab_label")),
     ('tab_desc', (By.CSS_SELECTOR, "input#tab_description"))])

box_form = Form(
    fields=
    [('box_label', (By.CSS_SELECTOR, "input#group_label")),
     ('box_desc', (By.CSS_SELECTOR, "input#group_description"))])

element_form = Form(
    fields=
    [('ele_label', (By.CSS_SELECTOR, "input#field_label")),
     ('ele_name', "//input[@id='field_name']"),
     ('ele_desc', (By.CSS_SELECTOR, "input#field_description")),
     ('choose_type', Select("//select[@id='field_typ']")),
     ('default_text_box', "//input[@id='field_default_value']"),
     ('add_button', "//img[@title='Add']")])


def _all_servicedialogs_add_new(context):
    sel.click("//div[@id='dialogs_tree_div']//td[.='All Dialogs']")
    cfg_btn('Add a new Dialog')
    sel.wait_for_element(label_form.label)

nav.add_branch(
    'automate_customization',
    {'service_dialogs': [nav.partial(accordion.click, 'Service Dialogs'),
                       {'service_dialog_new': _all_servicedialogs_add_new}]})


class ServiceDialog(Updateable):

    def __init__(self, label=None, description=None,
        submit=False, cancel=False,
        tab_label=None, tab_desc=None,
        box_label=None, box_desc=None,
        ele_label=None, ele_name=None,
        ele_desc=None, choose_type=None, default_text_box=None):
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

    def create(self):
        sel.force_navigate('service_dialog_new')
        fill(label_form, {'label': self.label,
                          'description_text': self.description,
                          'submit_button': self.submit,
                          'cancel_button': self.cancel})
        print self.tab_label
        if(self.tab_label is not None):
            plus_btn("Add a New Tab to this Dialog")
            sel.wait_for_element(tab_form.tab_label)
            fill(tab_form, {'tab_label': self.tab_label,
                        'tab_desc': self.tab_desc})
        if(self.box_label is not None):
            plus_btn("Add a New Box to this Tab")
            sel.wait_for_element(box_form.box_label)
            fill(box_form, {'box_label': self.box_label,
                        'box_desc': self.box_desc})
        if(self.ele_label is not None):
            plus_btn("Add a New Element to this Box")
            sel.wait_for_element(element_form.ele_label)
            fill(element_form, {'ele_label': self.ele_label,
                            'ele_name': self.ele_name,
                            'ele_desc': self.ele_desc,
                            'choose_type': self.choose_type,
                            'default_text_box': self.default_text_box})
        sel.click(element_form.add_button)
        sel.wait_for_element(message)
