import functools

import ui_navigate as nav
from cfme.web_ui import menu
assert menu

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui as web_ui
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Form, fill, Select, accordion, flash
from utils.update import Updateable


cfg_btn = functools.partial(tb.select, "Configuration")
plus_btn = functools.partial(tb.select, "Add")
message = "//div[@id='flash_msg_div']"
service_dialog_tree = web_ui.Tree('//div[@id="dialogs_treebox"]/div/table')
save_btn = "//img[@title='Save Changes']"

label_form = Form(
    fields=
    [('label', "//input[@id='label']"),
     ('description_text', "//input[@id='description']"),
     ('submit_button', "//input[@id='chkbx_submit']"),
     ('cancel_button', "//input[@id='chkbx_cancel']")])

tab_form = Form(
    fields=
    [('tab_label', "//input[@id='tab_label']"),
     ('tab_desc', "//input[@id='tab_description']")])

box_form = Form(
    fields=
    [('box_label', "//input[@id='group_label']"),
     ('box_desc', "//input[@id='group_description']")])

element_form = Form(
    fields=
    [('ele_label', "//input[@id='field_label']"),
     ('ele_name', "//input[@id='field_name']"),
     ('ele_desc', "//input[@id='field_description']"),
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
        {'service_dialog_new': _all_servicedialogs_add_new,
         'service_dialog': [lambda ctx: service_dialog_tree.click_path(ctx['dialog'].label),
            {'service_dialog_edit': nav.partial(cfg_btn, "Edit this Dialog")}]}]})


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
        flash.assert_no_errors()
        sel.wait_for_element(message)

    def update(self, updates):
        sel.force_navigate('service_dialog_edit',
            context={'dialog': self})
        fill(label_form, {'name_text': updates.get('name', None),
                          'description_text': updates.get('description', None)})
        sel.click(save_btn)
        flash.assert_no_errors()

    def delete(self):
        sel.force_navigate('service_dialog', context={'dialog': self})
        cfg_btn("Remove from the VMDB", invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()
